# generated by GPT-4

import requests
from bs4 import BeautifulSoup, NavigableString
import re
from tqdm.notebook import tqdm
import pandas as pd
import os
import yaml
import json
from sklearn.model_selection import train_test_split
import numpy as np
import textwrap
import sys


def download_website_content(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raises an HTTPError if the response status code is 4XX/5XX
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'html.parser')
        # text markup for which a space needs to be prepended and appended
        tags = ['a', 'span', 'li', 'strong', 'br', 'b', 'i', 'em', 'mark', 'small', 'del', 'ins', 'sub', 'sup']
        for element in soup.find_all(tags):
            element.insert_before(NavigableString(' '))
            element.insert_after(NavigableString(' '))

        return soup.get_text()
    except requests.RequestException as e:
        print(f"Failed to download {url}: {e}")
        return None


def save_content_to_file(content, path):
    # remove redundant whitespace
    content = '\n'.join(line for line in content.splitlines() if line.strip())
    while "  " in content:
        content = content.replace("  ", " ")
    content = '\n'.join(line.strip() for line in content.splitlines())

    with open(path, 'w', encoding='utf-8') as file:
        file.write(content)


def download_input_data(input_file, output_dir, overwrite=False):
    os.makedirs(output_dir, exist_ok=True)
    df = pd.read_csv(input_file)

    # Group by 'journal_abbr' and 'website'
    grouped = df.groupby(['journal_abbr', 'website'])

    # Initialize tqdm progress bar
    pbar = tqdm(total=len(grouped), desc="Downloading Content")

    downloaded_pages = 0

    for (journal_abbr, url), _ in grouped:

        filename = f"{output_dir}/{re.sub(r'[. ]', '', journal_abbr)}.txt"

        # no need to download if we don't have a URL or the website has already been downloaded
        if pd.isna(url) or (os.path.exists(filename) and not overwrite):
            pbar.update(1)
            continue

        content = download_website_content(url)
        if content:
            save_content_to_file(content, filename)
            downloaded_pages += 1
        else:
            print(f"Failed to retrieve content for {journal_abbr} - {url}")
        pbar.update(1)

    pbar.close()

    print(f'Downloaded {downloaded_pages} web pages.')


def wrap_content_generator(content, width=80):
    for line in content.splitlines(keepends=True):
        if line.strip() == '':
            yield '\n'
        else:
            for line2 in textwrap.wrap(line, width=width):
                yield line2


def clean_values(row):
    """Return a new dictionary with no NaN, None, or empty/whitespace-only values."""
    return {k: v for k, v in row.items() if pd.notna(v) and v is not None and v.strip()}


def filter_content_with_context(content, keywords, lines_before=1, lines_after=1, max_chars=None):
    lines = content.splitlines()
    filtered_content = ""
    keyword_threshold = 1  # Start with requiring at least 1 keyword to be present

    while True:
        matched_lines = set()
        for i, line in enumerate(lines):
            # Count how many keywords are present in the line
            keywords_present = sum(bool(re.search(r'\b' + re.escape(keyword) + r'\b', line)) for keyword in keywords)
            # If the number of present keywords meets or exceeds the threshold, include the line
            if keywords_present >= keyword_threshold:
                context_range = range(max(i - lines_before, 0), min(i + lines_after + 1, len(lines)))
                matched_lines.update(list(context_range))

        # Extract the matched lines and their context
        filtered_lines = [lines[i] for i in sorted(matched_lines)]
        filtered_content = "\n".join(filtered_lines)

        # Check if the filtered content meets the max_chars condition or if there's no max_chars limit
        if max_chars is None or len(filtered_content) <= max_chars:
            break  # Condition met or no limit specified; stop filtering

        # Increase the keyword threshold for stricter filtering if the content is too long
        keyword_threshold += 1
        # If every line requires more keywords than are available, it's impossible to meet the condition
        if keyword_threshold > len(keywords):
            return ""  # Return empty string as the condition cannot be fulfilled

    return filtered_content


def create_training_file(instruction: str,
                         template_func: callable,
                         input_file: str, output_dir: str, content_dir: str,
                         cols_to_remove: list, column_to_filter_by: str,
                         record_identifier_col: str,
                         max_chars=2048 * 4, max_gt_items=10,
                         line_width=120, lines_before=1, lines_after=1, random_seed=None,
                         debug=True):


    # Load the input
    df = pd.read_csv(input_file)

    # Set or generate a random seed
    if random_seed is None:
        random_seed = np.random.randint(0, 10000)

    # Prepare the output directory
    os.makedirs(output_dir, exist_ok=True)

    # Keep track of the longest prompts
    id_value_pairs = {}

    def process_and_write_data(grouped_df, file, write_debug_file=False):
        for id, group in grouped_df.groupby(record_identifier_col):

            # use only the first 10 ground truth items so that the training record does not become too large
            group = group.head(max_gt_items)

            # load website content from the cache
            filename = f"{content_dir}/{re.sub(r'[. ]', '', str(id))}.txt"
            try:
                with open(filename, 'r', encoding='utf-8') as content_file:
                    content = content_file.read()
            except FileNotFoundError:
                continue

            # Clean up data
            answer_df = group.drop(cols_to_remove, axis=1, errors='ignore').dropna(axis=1, how='all')

            # Convert DataFrame rows to YAML dictionaries, cleaning NaN values
            cleaned_rows = answer_df.apply(lambda row: clean_values(row.to_dict()), axis=1)
            answer = yaml.dump(list(cleaned_rows), allow_unicode=True, sort_keys=False)

            # wrap content to decrease token window
            lines = [line for line in wrap_content_generator(content, width=line_width)]
            wrapped_content = '\n'.join(lines)

            # Determine how many characters are available for the content
            max_chars_for_content = max_chars - len(instruction) - len(answer)

            # Determine which keywords to filter by
            keyword_list = [x for x in group[column_to_filter_by].tolist() if pd.notnull(x)]

            # Filter rows, using keywords and a context window
            filtered_content = filter_content_with_context(wrapped_content,
                                                           keywords=keyword_list,
                                                           lines_before=lines_before, lines_after=lines_after,
                                                           max_chars=max_chars_for_content)

            # Ignore if nothing was found
            if filtered_content.strip() == '':
                continue

            if write_debug_file:
                sequence = [
                    '### JOURNAL', id,
                    '### URL', group['website'].tolist()[0],
                    '### CONTENT', filtered_content,
                    '### ANSWER', answer,
                    '-' * line_width,
                    ''
                ]
                file.write('\n\n'.join(sequence))
            else:
                sequence = template_func(instruction, filtered_content, answer)
                train_json = {
                    "id": id,
                    "text": sequence
                }
                file.write(json.dumps(train_json) + '\n')
                id_value_pairs[id] = len(sequence)

    # Split the DataFrame into training (80%) and test+validation (20%)
    train_df, test_valid_df = train_test_split(df, test_size=0.2, random_state=random_seed)

    # Further split the test+validation into test and validation (50% each of the 20%)
    test_df, valid_df = train_test_split(test_valid_df, test_size=0.5, random_state=random_seed)

    # Debug file for better readability of the result
    if debug:
        debug_instruction = instruction.replace('\n', '\n\n')
        debug_instruction = "\n".join(textwrap.wrap(debug_instruction, width=line_width))
        with open(f'{output_dir}/debug.txt', 'w', encoding='utf-8') as debug_file:
            debug_file.write(f'### INSTRUCTION\n\n{debug_instruction}\n\n{"=" * line_width}\n\n')
            process_and_write_data(df, debug_file, write_debug_file=True)

    # Write train, test and validation files
    with open(f'{output_dir}/train.jsonl', 'w', encoding='utf-8') as train_file, \
            open(f'{output_dir}/test.jsonl', 'w', encoding='utf-8') as test_file, \
            open(f'{output_dir}/valid.jsonl', 'w', encoding='utf-8') as valid_file:

        # Process and write data to each file
        process_and_write_data(train_df, train_file)
        process_and_write_data(test_df, test_file)
        process_and_write_data(valid_df, valid_file)

    if debug:
        print("Length of generated sequences:")
        print(f" - max: {max(id_value_pairs.values())}")
        print(f" - avg: {sum(id_value_pairs.values()) / len(id_value_pairs)}")

        sorted_pairs = sorted(id_value_pairs.items(), key=lambda x: x[1], reverse=True)
        highest_10_values = sorted_pairs[:10]
        print("Longest sequences:")
        for _id, value in highest_10_values:
            print(f"{_id}: {value}")

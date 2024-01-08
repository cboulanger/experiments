# written with help from ChatGPT-4 and using code from the googlesearch python module
# (see https://github.com/Nv7-GitHub/googlesearch)

import requests
import re
import random
from requests.exceptions import HTTPError, ConnectionError
from time import sleep
from bs4 import BeautifulSoup
from pypdf import PdfReader
from io import BytesIO


def get_useragent():
    return random.choice(_useragent_list)


_useragent_list = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36 Edg/111.0.1661.62',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/111.0'
]


def _req(term, results, lang, start, proxies, timeout, retry=3, delay_before_retry=5, filetype: str = "html"):
    while retry > 0:
        try:
            resp = requests.get(
                url="https://www.google.com/search",
                headers={
                    "User-Agent": get_useragent()
                },
                params={
                    "q": term,
                    "num": results + 2,  # Prevents multiple requests
                    "hl": lang,
                    "start": start,
                    "filetype": filetype
                },
                proxies=proxies,
                timeout=timeout
            )
            resp.raise_for_status()
            return resp

        except ConnectionError as err:
            print(f'Connection error: {err}. Retrying in {delay_before_retry} seconds.')
            retry -= 1
            sleep(delay_before_retry)

    raise ConnectionError("Too many retries.")


def _search(term, num_results=10, lang="en", proxies=None, sleep_interval=0, timeout=5, retry=3, delay_before_retry=5):
    """The Google search implementation """

    escaped_term = term.replace(" ", "+")

    # Fetch
    start = 0
    while start < num_results:
        # Send request
        resp = _req(escaped_term, num_results - start, lang, start, proxies, timeout, retry=retry,
                    delay_before_retry=delay_before_retry)
        # Parse
        soup = BeautifulSoup(resp.text, "html.parser")
        result_block = soup.find_all("div", attrs={"class": "g"})
        found_valid_result = False
        for result in result_block:
            # Find link, title, description
            link = result.find("a", href=True)
            title = result.find("h3")
            description_box = result.find("div", {"style": "-webkit-line-clamp:2"})
            if description_box:
                description = description_box.text
                if link and title and description:
                    start += 1
                    found_valid_result = True
                    yield link["href"]
                    break
        if not found_valid_result:
            break

        sleep(sleep_interval)


def run_google_search(query, num_results=3, lang="en", sleep_interval=4, exclude: list = None, timeout=10,
                      proxy=None, verbose: bool = False) -> list:
    """
    Fetches and returns search results for a given query.

    This function sends a request to a search engine using the specified parameters and retrieves the text content of
    the search results. It avoids URLs listed in the 'exclude' parameter.

    Parameters:
    - query (str): The Google search query.
    - num_results (int, optional): The number of search results to retrieve. Defaults to 3.
    - lang (str, optional): The language for the search results. Defaults to "en" (English).
    - sleep_interval (int, optional): The delay in seconds between requests of additional result pages
      to avoid hitting rate limits. Defaults to 2 seconds.
    - max_char (int, optional): The maximum number of characters to fetch from the search results. Defaults to 8000.
    - exclude (list, optional): A list of regular expressions representing URLs to exclude from the search results.
    - timeout (int, optional): the timeout for the http query

    Returns:
    - A list of urls of length `num_results`

    """

    if verbose:
        print(f'Searching google for {query}...')

    proxies = None
    if proxy:
        if proxy.startswith("https"):
            proxies = {"https": proxy}
        else:
            proxies = {"http": proxy}

    urls = _search(query, num_results=num_results, lang=lang, sleep_interval=sleep_interval, timeout=timeout,
                   proxies=proxies)

    if exclude is None:
        exclude = []
    return [url for url in urls if not any(re.search(e, url) for e in exclude)]


def clean_text(text):
    # Remove extra whitespace and empty lines
    cleaned_text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    return cleaned_text


def download(url: str, max_char: int = 8000, timeout: int = 10, retry: int = 3, delay_before_retry: int = 5,
             verbose: bool = False) -> str | None:
    if verbose:
        print(f'Downloading content of {url}...')
    _retry = retry
    while _retry > 0:
        try:
            response = requests.get(
                url=url,
                headers={
                    "User-Agent": get_useragent()
                },
                timeout=timeout)
            response.raise_for_status()

            content_type = response.headers.get('Content-Type', '').split(';')[0]  # Extract the primary content type

            match content_type:
                case 'application/pdf':
                    reader = PdfReader(BytesIO(response.content))
                    first_page_content = reader.pages[0].extract_text()
                    return first_page_content[:max_char]

                case 'text/html':
                    soup = BeautifulSoup(response.text, "html.parser")
                    full_text = soup.get_text()
                    full_text = clean_text(full_text)
                    return full_text[:max_char]

                case _:
                    print(f"Cannot parse {content_type}")
                    return None

        except ConnectionError as err:
            print(f'Connection error: {err}. Retrying in {delay_before_retry} seconds.')
            _retry -= 1
            sleep(delay_before_retry)
        except HTTPError as err:
            if err.response.status_code == 403:
                print("Got 403 (Forbidden) error. Skipping...")
                return None
            raise RuntimeError(f"Error: {err.response.status_code} {err.response.reason}:\n{err.response.text}")

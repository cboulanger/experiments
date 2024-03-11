# code written with the help of GPT-4

import requests
from bs4 import BeautifulSoup
import urllib.parse
from lxml import etree
import pandas as pd

def generate_query_string(person, startRecord):
    base_url = "https://services.dnb.de/sru/dnb"
    query = f'per="{person}"'
    encoded_query = urllib.parse.quote(query)
    query_url = f"{base_url}?operation=searchRetrieve&version=1.1&query={encoded_query}&recordSchema=oai_dc&maximumRecords=100&startRecord={startRecord}"
    return query_url

def fetch_data(person, start_record):
    url = generate_query_string(person, start_record)
    response = requests.get(url)
    xml_data = response.content

    soup = BeautifulSoup(xml_data, 'lxml-xml')
    diagnostics = soup.find('diagnostics')
    if diagnostics:
        diag_message = diagnostics.find('message').text
        diag_details = diagnostics.find('details').text
        print(f"Error: {diag_message} - {diag_details}")
        return None
    return xml_data

def parse_records(xml_data):
    ns = {
        "oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/",
        "dc": "http://purl.org/dc/elements/1.1/",
        "srw": "http://www.loc.gov/zing/srw/"
    }

    root = etree.fromstring(xml_data)
    records = root.xpath('//srw:record', namespaces=ns)
    num_records = int(root.xpath('//srw:numberOfRecords', namespaces=ns)[0].text)

    results = []

    for record in records:
        title_elements = record.xpath('.//dc:title', namespaces=ns)
        if not title_elements:
            continue
        title = title_elements[0].text

        authors = record.xpath('.//dc:creator', namespaces=ns)
        author_list = []
        for author in authors:
            author_list.append(author.text)
        authors_str = '; '.join(author_list)

        publication_year_elements = record.xpath('.//dc:date', namespaces=ns)
        if publication_year_elements:
            publication_year = publication_year_elements[0].text
        else:
            publication_year = ""

        results.append([title, authors_str, publication_year])

    return results, num_records


def get_publications(person):
    start_record = 1
    retrieved_records = 0
    data = []  # Initialize an empty list to store the data

    # The structure of the DataFrame columns
    columns = ['Title', 'Author', 'Publication Year']

    while True:
        xml_data = fetch_data(person, start_record)
        if xml_data is not None:
            results, num_records = parse_records(xml_data)
            if not results:
                break

            data.extend(results)

            retrieved_records += len(results)
            start_record += len(results)

            if retrieved_records >= num_records:
                break

    # Convert the list of data to a pandas DataFrame
    df = pd.DataFrame(data, columns=columns)
    return df



import os

import requests
from dotenv import load_dotenv

load_dotenv()

def get_dois_years(issn):
    url = f"https://api.crossref.org/journals/{issn}"
    email = os.getenv('CROSSREF_EMAIL')
    headers = {'User-Agent': f'Python-requests/2.23.0 (mailto:{email})'}
    response = requests.get(url, headers=headers)

    # Check if the request was successful
    if response.status_code == 404:
        return None

    data = response.json()

    # Extract the array of [year, number of DOIs]
    years_info = data.get("message", {}).get("breakdowns", {}).get("dois-by-issued-year", [])

    if not years_info:
        return ""

    # Sort the years_info by year
    years_info.sort(key=lambda x: x[0])

    # Initialize variables for tracking
    years_list = []
    start_year = None
    last_year = None

    for year, _ in years_info:
        if start_year is None:
            # This is the first year in a sequence
            start_year = year
            last_year = year
        elif year == last_year + 1:
            # This year is a continuation of the sequence
            last_year = year
        else:
            # This year is not a continuation; close the previous sequence and start a new one
            years_list.append(f"{start_year}-{last_year}")
            start_year = year
            last_year = year

    # Add the last sequence to the list
    years_list.append(f"{start_year}-{last_year}")

    return ", ".join(years_list)



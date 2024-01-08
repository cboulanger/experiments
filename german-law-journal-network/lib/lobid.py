# written with the help of ChatGPT4
import requests
import time
import json
from requests import Response


def _query_lobid_api(url, params: dict = None, headers: dict = None):
    for attempt in range(4):  # Try up to four times (initial + 3 retries)
        try:
            response: Response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()  # This will raise an HTTPError if the HTTP request returned an unsuccessful status code
            result = response.json()
            with open('tmp/lobid-result.json', "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
            return result

        except requests.exceptions.HTTPError as http_err:
            raise Exception(f"HTTP error occurred: {http_err}") from None
        except requests.exceptions.Timeout:
            if attempt == 3:  # Give up after 3 retries
                raise Exception("Maximum retry attempts reached after timeout") from None
            time.sleep(2)  # Wait for 2 seconds before retrying
        except requests.exceptions.RequestException as err:
            raise Exception(f"Error occurred during request: {err}") from None
        except ValueError as json_err:
            raise Exception(f"JSON decoding error: {json_err}\nResponse text: {response.text}") from None

    return None  # In case the loop completes without returning


def run_query(query: str, fields: list = None):
    # clean up query
    query = query.strip().replace("\n", " ")

    # Endpoint for the lobid.org API
    url = 'http://lobid.org/resources/search'

    # prepare and run query
    params = {
        'q': query,
        'format': "json"
    }
    headers = {
        'Accept': 'application/x-jsonlines'
    }

    result = _query_lobid_api(url, params, headers)
    member = result['member']
    return [({k: _dig(r, k) for k in fields} if fields else r) for r in member]


def _dig(dictionary, path, *additional_keys):
    # Split the path if it's a string, otherwise use it as-is
    keys = path.split('.') if isinstance(path, str) else [path]

    # Add any additional keys from *additional_keys
    keys.extend(additional_keys)

    current_level = dictionary
    for key in keys:
        if isinstance(current_level, dict) and key in current_level:
            current_level = current_level[key]
        elif isinstance(current_level, list) and key.isdecimal():
            current_level = current_level[int(key)]
        else:
            return None
    return current_level


def get_resource(resource_id: str, fields: list = None):
    if resource_id.startswith("http"):
        resource_id = resource_id.replace('#', '').replace('!', '')
        url = f'{resource_id}.json'
    else:
        url = f'http://lobid.org/resources/{resource_id}.json'
    # run query and return (filtered) result
    result: dict = _query_lobid_api(url)
    return ({k: _dig(result, k) for k in fields}) if fields else result

#%%

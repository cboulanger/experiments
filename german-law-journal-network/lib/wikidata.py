# written by ChatGPT4
import requests
import time

def run_query(query):
    url = 'https://query.wikidata.org/sparql'
    headers = {
        'User-Agent': 'CoolBot/0.0 (https://example.org/coolbot/; coolbot@example.org)'
    }

    for attempt in range(4):  # Try up to four times (initial + 3 retries)
        try:
            response = requests.get(url, params={'format': 'json', 'query': query}, headers=headers, timeout=10)
            response.raise_for_status()  # This will raise an HTTPError if the HTTP request returned an unsuccessful status code
            return response.json()

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



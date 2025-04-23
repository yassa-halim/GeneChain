import time
import requests
from requests.exceptions import RequestException, HTTPError

from utils.helper_functions import get_custom_logger
from config import OXYLABS_SEARCH_URL, OXYLABS_USERNAME, OXYLABS_USER_PASSWORD, OXYLABS_SEARCH_SOURCE

log = get_custom_logger(name=__name__)

def send_request_with_retry(payload: dict, retries: int = 3, delay: int = 2) -> dict:
    for attempt in range(retries):
        try:
            response = requests.post(
                OXYLABS_SEARCH_URL, json=payload, 
                auth=(OXYLABS_USERNAME, OXYLABS_USER_PASSWORD)
            )
            response.raise_for_status()
            return response.json()
        except (RequestException, HTTPError) as e:
            log.error(f"Request failed on attempt {attempt + 1}: {e}")
            if attempt < retries - 1:
                log.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                raise e  # Raise the last error after retries are exhausted

def get_oxylabs_search_result(search_engine: str, user_query: str, geo_location: str = 'United States') -> dict:
    log.info(f"Sending request to Oxylabs with search engine: {search_engine} and query: {user_query}.")
    start_time = time.time()

    payload = {
        'source': search_engine,
        'domain': 'com',
        'query': user_query,
        'parse': 'true',
        'geo_location': geo_location,
        'pages': 1,
    }

    try:
        data = send_request_with_retry(payload)
        if 'results' in data:
            data = data['results'][0]['content']
            if search_engine == OXYLABS_SEARCH_SOURCE:
                data = {"products": data['results']['organic']}
        else:
            log.warning("No results found in the Oxylabs response.")
            return {}

    except (RequestException, HTTPError) as e:
        log.error(f"Failed to get Oxylabs search result: {e}")
        return {}

    log.info(f"Oxylabs response took {(time.time() - start_time):.2f} seconds with search engine: {search_engine}.")
    return data

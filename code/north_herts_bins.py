from datetime import datetime
import logging
from dateutil import parser
import re
from typing import List, Tuple
from urllib.parse import urlparse, parse_qsl, urlencode, urljoin
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger()

HOME_URL = 'https://uhtn-wrp.whitespacews.com/mop.php#!'
SEARCH_URL_CONTAINS = 'serviceID=A'

def get_north_herts_bins(number: str, postcode: str) -> List[Tuple[datetime, str]]:
    address_name_number = number
    address_postcode = postcode

    # get the NHDC Waste and Recycling home page
    home_page_request = requests.get(HOME_URL)

    home_page_soup = BeautifulSoup(home_page_request.content, 'html.parser')

    # look for the link that contains the search url
    link = home_page_soup.find('a', href=re.compile(SEARCH_URL_CONTAINS))

    search_url = link['href']

    # the address search url to post to is just the form url with seq=2 instead of seq=1
    # so build that url here
    params = {'seq': '2'}
    url_parts = urlparse(search_url)
    query = dict(parse_qsl(url_parts.query))
    query.update(params)

    search_action_url = url_parts._replace(query=urlencode(query)).geturl()

    # post to retrieve address results
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {'address_name_number': address_name_number, 'address_postcode': address_postcode}
    results_request = requests.post(search_action_url, data=data, headers=headers)

    results_soup = BeautifulSoup(results_request.content, 'html.parser')

    link = results_soup.find('a', href=re.compile(SEARCH_URL_CONTAINS))

    results_url = link['href']

    # log the full address name found
    logger.info(link.text)

    # the link href they provide is relative so join it to our base url before making request
    final_url = urljoin(HOME_URL, results_url)

    final_request = requests.post(final_url, headers=headers)

    final_soup = BeautifulSoup(final_request.content, 'html.parser')

    # find all collection dates and descriptions and clean them into a list of tuples
    lis = final_soup.find_all('li')
    lis_strings = list(map(lambda l: l.text.strip(), lis))

    def chunks(lst, n):
        """Yield successive n-sized chunks from lst."""
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

    uncleaned_list = list(chunks(lis_strings, 3))
    cleaned_list = [row for row in uncleaned_list if len(row) == 3]
    cleaned_list = [(parser.parse(row[1], dayfirst=True), row[2]) for row in cleaned_list]

    return(cleaned_list)
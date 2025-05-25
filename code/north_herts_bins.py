from datetime import datetime
import logging
from dateutil import parser
import re
from typing import List, Tuple
from bs4 import BeautifulSoup
from selenium import webdriver
import time
from contextlib import closing
import os, dotenv

# Load environment variables from .env file
dotenv.load_dotenv()

logger = logging.getLogger()
# url should be your address's waste and recycling collection page


def get_north_herts_bins() -> List[Tuple[datetime, str]]:
    """
    Given a specified house number and postcode, scrapes NHDC Waste and
    Recycling portal for upcoming bin collections and returns a List of
    Tuples (collection_date, collection_description)
    """
    HOME_URL = os.getenv("HOME_URL")
    if not HOME_URL:
        raise ValueError("HOME_URL environment variable is not set.")
    else:
        date_pattern = re.compile(
            r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+(\d{1,2}(?:st|nd|rd|th)?\s+\w+\s+\d{4})"
        )
        with closing(webdriver.Chrome()) as driver:
            logger.info("Setting up Chrome driver for North Herts bins scraping...")
            # Set up the Chrome driver
            driver.implicitly_wait(10)  # Wait for elements to load
            driver.get(HOME_URL)
            time.sleep(3)  # Wait for JS to load — tweak this as needed

            soup = BeautifulSoup(driver.page_source, "html.parser")
            raw_text = [
                span.get_text()
                for span in soup.find_all("span", class_="value-as-text")
            ]
            logger.info("Scraped raw text from North Herts bins page.")

        # find the date matches and their index in the raw_text
        collection_dates = [
            (i, date_pattern.search(item).group(0))
            for i, item in enumerate(raw_text)
            if date_pattern.search(item)
        ]
        parsed_dates = [(i, parser.parse(date_str)) for i, date_str in collection_dates]
        # next_collection_date = min(date for _, date in parsed_dates)

        # match bins to the bin date and only get the bins in the next collection date
        matched_bins = [(date, raw_text[i - 1]) for i, date in parsed_dates]

        return matched_bins


if __name__ == "__main__":
    if HOME_URL:
        result = get_north_herts_bins()
        print(result)
    else:
        raise ValueError("HOME_URL environment variable is not set.")

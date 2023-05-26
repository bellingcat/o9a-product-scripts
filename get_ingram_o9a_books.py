"""Get information about a list of in-stock O9A books from Ingram's catalog.
This provides the same information as is available using Ingram's Stock Check app
https://www.ingramcontent.com/retailers/independent-bookstores/stock-check-app"""

import requests
import pandas as pd

# Base URL of Ingram API
BASE_URL = "https://ipage.ingramcontent.com/ipage/ws/1/mobile"

# List of EAN (European Article Number) codes for books associated with O9A
EANS = [
    "9780692306581",
    "9780997836363",
    "9780692575505",
    "9781494440954",
    "9780692260845",
    "9780692548127",
    "9780692723920",
    "9780999768006",
    "9781696821742",
    "9781687255624",
    "9781689931953",
    "9780997836370",
    "9780999768044",
    "9780999768020",
    "9780997836387",
    "9780997836356",
    "9780997836349",
    "9780997836325",
    "9780997836301",
    "9780997836318",
    "9780692667293",
    "9780692510711",
    "9780692484463",
    "9780692432082",
]

# Columns in API response to store
RELEVANT_COLUMNS = [
    "primaryContributorName",
    "isbn",
    "title",
    "primaryProductType",
    "displayableFormat",
    "sortableTitle",
    "ean",
    "primaryBisacCategory",
    "publisher",
    "retailPrice",
    "totalOnHand",
]

# Write information about each book to this file
OUTPUT_CSV = "o9a_books.csv"


class IngramClient:
    """Class to search Ingram's free (mobile) API."""

    def __init__(self):
        self.token = self.get_token()

    def get_token(self):
        """Initialize access token, which is necessary for all API queries"""

        params = {
            "email_address": "email@address.com",  # email address doesn't seem to matter
            "terms_accepted": True,
        }

        r = requests.post(url=BASE_URL + "/register", json=params)
        return r.json()["token"]

    def search(self, keywords):
        """Search Ingram's book catalog for a given keyword or EAN"""

        all_results = []
        page_number = 1
        while True:
            params = {
                "keywords": keywords,
                "token": self.token,
                "page_number": page_number,
            }
            r = requests.get(url=BASE_URL + "/search", params=params)
            if not (results := r.json().get("results")):
                break

            enhanced_results = []
            for result in results:
                additional_info = self.get_stock(ean=result["ean"])
                result.update(additional_info)
                enhanced_results.append(result)
            all_results.extend(enhanced_results)

            page_number += 1
        return all_results

    def get_stock(self, ean):
        """Query how many copies of a given Ingram product are in stock"""

        params = {"product_code": ean, "token": self.token}
        r = requests.get(url=BASE_URL + "/stockcheck", params=params)
        return r.json()


def process_book(book):
    """Extract relevant fields from Ingram API response, aggregate number of books in-stock"""

    processed_book = {k: v for k, v in book.items() if k in RELEVANT_COLUMNS}
    processed_book["contributors"] = ", ".join(
        c["displayName"] for c in book["contributors"]
    )
    processed_book["totalOnOrder"] = sum(c["count"] for c in book["onOrder"].values())
    return processed_book


if __name__ == "__main__":
    # Initialize client, fetch information about all specified books and store in DataFrame
    client = IngramClient()
    valid_books = []
    for ean in EANS:
        valid_books.extend(client.search(keywords=ean))
    df = pd.DataFrame([process_book(book) for book in valid_books])

    # Write DataFrame to CSV file
    df.to_csv(path_or_buf=OUTPUT_CSV, index=False, quoting=2)

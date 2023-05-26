"""Find all Barnes & Noble stores with a specified product in-stock
"""

from bs4 import BeautifulSoup
import requests

# Base URL for Barnes & Noble product availability API
BASE_URL = "https://www.barnesandnoble.com/xhr/storeList-with-prodAvailability.jsp"

# Stock-keeping unit number for specific book
SKU_ID = 9780692306581

# Zip code to center search on
ZIP_CODE = 75254

# Radius of search: Barnes & Noble's browser interface only allows maximum of 100 miles
SEARCH_RADIUS = 1000

# Random user-agent
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 8.0.0; 5099D Build/O00623) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.68 Mobile Safari/537.36"
}


def process_store(store_soup):
    """Extract relevant information from HTML of a given store"""

    in_stock_str = store_soup.select_one("div.item-in-stock").text.strip()
    if in_stock_str == "In Stock in Store":
        in_stock = True
    elif in_stock_str == "Not in Stock in Store":
        in_stock = False
    else:
        in_stock = in_stock_str

    return {
        "store": store_soup.select_one(
            "div.store-details-container > div.store-address"
        ).text.strip(),
        "in_stock": in_stock,
    }


if __name__ == "__main__":
    # Initialize query parameters
    params = {
        "action": "fromSearch",
        "radius": SEARCH_RADIUS,
        "searchString": ZIP_CODE,
        "skuId": SKU_ID,
    }

    # Make API query to determine which (if any) stores have the book in-stock
    r = requests.get(url=BASE_URL, params=params, headers=HEADERS)
    soup = BeautifulSoup(r.text, features="lxml")
    stores = soup.select("div.store-list")
    results = [process_store(store) for store in stores]

    # Print addresses of stores with book in-stock
    [print(result["store"]) for result in results if result["in_stock"]]

"""Estimate the total revenue of a given Ebay seller, and identify their most
frequently reviewed products"""

import requests
from urllib.parse import urlencode, quote
from collections import Counter

from bs4 import BeautifulSoup
import pandas as pd

# URL of Ebay's customer feedback API
BASE_URL = "https://feedback.ebay.com/fdbk/update_feedback_profile"

# Username of seller
USERNAME = "commandantcultus"

# Nested dict of parameters in API query
PARAMS = {
    "url": {
        "username": USERNAME,
        "filter": "feedback_page:RECEIVED_AS_SELLER",
        "limit": "200",
    },
    "module": {"modules": "FEEDBACK_SUMMARY"},
}


def process_review(review):
    """Extract relevant fields from raw JSON response for one review"""

    item = review["feedbackInfo"]["item"]
    item_text = item["itemSummary"]["textSpans"][0]["text"]
    name, item_id = item_text.split(" (#")

    return {
        "name": name,
        "id": int(item_id.strip(")")),
        "price": float(item["itemPrice"]["textSpans"][0]["text"].replace("US $", "")),
    }


if __name__ == "__main__":
    # Fetch data from Ebay API, convert into DataFrame
    params_str = "&".join(f"{k}={quote(urlencode(v))}" for k, v in PARAMS.items())
    r = requests.get(url=BASE_URL, params=params_str)
    review_dicts = r.json()["modules"]["FEEDBACK_SUMMARY"]["feedbackView"][
        "feedbackCards"
    ]
    reviews = pd.DataFrame(
        [process_review(review_dict) for review_dict in review_dicts]
    )

    # Fetch total number of sales (should be 581 as of May 2023)
    r = requests.get(f"https://www.ebay.com/usr/{USERNAME}")
    soup = BeautifulSoup(r.content, features="lxml")
    total_reviews = int(
        soup.select("div.str-seller-card__stats-content > div[title]")[1][
            "title"
        ].split("  ")[0]
    )

    # Estimate seller's total revenue
    estimated_revenue = reviews["price"].mean() * total_reviews
    print(f"Estimated revenue of seller: ${estimated_revenue:.2f}")

    # Identify 5 most frequently reviewed items
    print("Most reviewed items:")
    print(Counter(reviews["name"]).most_common(5))

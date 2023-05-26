"""Identify all articles from o9a.org that have been captured on Wayback Machine but 
have since been deleted from the o9a.org website, and search for articles containing
the term "tempel".
"""

import re
import time

import requests
import pandas as pd
from bs4 import BeautifulSoup

# URL of Wayback Machine search API
BASE_URL = "http://web.archive.org/cdx/search/cdx"

# If archived URL contains these strings, ignore it
IGNORE_URL_STRINGS = ["wp-json", "wp-content", "/uploads/", "/page/"]

# Search articles for this string
SEARCH_TERM = "tempel"

# Save table of information for deleted articles to this file
OUTPUT_CSV = "o9a_deleted_articles.csv"


def get_wayback_url(row):
    """Convert timestamp and original URL into Wayback Machine URL"""

    return f'https://web.archive.org/web/{row["timestamp"]}/{row["original"]}'


def process_archived_url(url):
    """Convert original archived URL to standard form"""

    if "/20" not in url:
        return None
    _url = url.split("?")[0]
    _url = _url.replace(".org:80/", ".org/").replace("http://", "https://").strip("/")
    if any(s in _url for s in IGNORE_URL_STRINGS):
        return None
    if re.match("^https://www.o9a.org/\d{4}/\d{2}$", _url):
        return None
    if _url.endswith("/embed"):
        return None
    return _url


def _get(url):
    """Wrapper for retrying request multiple times."""

    n_retries = 0

    while n_retries < 5:
        time.sleep(2**n_retries - 1)
        try:
            response = requests.get(url=url, timeout=15)
            if response.status_code == 200:
                return response
            else:
                n_retries += 1
        except Exception:
            n_retries += 1

    raise ValueError(
        f"Maximum number of retries reached for GET request with url {url}"
    )


def process_article(soup):
    """Extract relevant information from HTML of o9a.org article"""

    content_soup = soup.select_one("div#content")
    content = content_soup.text.strip()

    tags_split = content.split("| Tags: ")
    if len(tags_split) > 1:
        tags = tags_split[1].split(" | ")[0].split(", ")
    else:
        tags = []

    data = {
        "wayback_url": soup.find("link", {"rel": "canonical"})["href"],
        "title": content_soup.find("h1").text,
        "author": content.split("| Author: ")[1].split(" | ")[0],
        "date": content.split("Posted: ")[1].split(" | ")[0],
        "content": content.lower(),
        "links": [a["href"] for a in content_soup.find_all("a", href=True)],
        "tags": tags,
    }
    return data


if __name__ == "__main__":
    # Get all archived pages from the o9a.org website, store in DataFrame
    capture_list = []
    page = 0
    out_of_pages = False
    while not out_of_pages:
        params = {
            "page": page,
            "url": f"o9a.org/*",
            "output": "json",
        }
        r = requests.get(url=BASE_URL, params=params)
        if r.text == "":
            out_of_pages = True
            break
        result = r.json()
        capture_list.append(pd.DataFrame(data=result[1:], columns=result[0]))
        page += 1
    captures = pd.concat(capture_list)
    captures["datetime"] = pd.to_datetime(captures["timestamp"])
    captures["url"] = captures.apply(get_wayback_url, axis="columns")
    captures = (
        captures[captures["statuscode"] == "200"]
        .sort_values("timestamp")
        .reset_index(drop=True)
    )
    captures["processed_url"] = captures["original"].apply(process_archived_url)
    captures = captures.drop_duplicates(subset="processed_url", keep="first")

    # Get all URLs from the o9a.org sitemap, compare with archived URLs to find deleted articles
    r = requests.get("https://www.o9a.org/wp-sitemap-posts-post-1.xml")
    soup = BeautifulSoup(r.content, features="lxml")
    article_urls_sitemap = set([loc.text.strip("/") for loc in soup.select("url loc")])
    article_urls_wayback = set(captures["processed_url"].dropna())
    deleted_urls = article_urls_wayback - article_urls_sitemap
    urls_to_download = captures[captures["processed_url"].isin(deleted_urls)]["url"]

    # Download all deleted pages, process into DataFrame and save to CSV
    article_data = []
    for url in urls_to_download:
        r = _get(url)
        soup = BeautifulSoup(r.content, features="lxml")
        article_data.append(process_article(soup))
    articles = pd.DataFrame(article_data)
    articles["date"] = pd.to_datetime(articles["date"])
    articles = articles.sort_values("date").reset_index(drop=True)
    articles.to_csv(path_or_buf=OUTPUT_CSV, index=False, quoting=2)

    # Search for specified search term in deleted article contents
    relevant_articles = articles[
        articles["content"].str.contains(SEARCH_TERM, na=False)
    ][["date", "wayback_url"]]
    for date, url in relevant_articles.values:
        print(date, url)

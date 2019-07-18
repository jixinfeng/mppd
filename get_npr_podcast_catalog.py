import json
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor


def get_rss_from_page(podcast):
    title, page_url = podcast
    page_html = requests.get(page_url).text
    page_soup = BeautifulSoup(page_html, 'html.parser')
    page_rss = page_soup.find('a', string='RSS link')['href']
    return title, page_rss


def get_npr_podcasts_catalog():
    catalog_url = 'https://www.npr.org/programs/'
    catalog_html = requests.get(catalog_url).text
    catalog_soup = BeautifulSoup(catalog_html, 'html.parser')
    link_block = catalog_soup.find_all('a')
    podcast_list = [
        (l.getText().strip(), l['href'])
        for l in link_block
        if l['href'].startswith('https://www.npr.org/podcasts/')
    ]

    with ThreadPoolExecutor() as mt_pool:
        podcast_rss_feeds = mt_pool.map(get_rss_from_page, podcast_list)

    podcast_catalog = {}
    for i, podcast in enumerate(podcast_rss_feeds):
        title, rss_url = podcast
        podcast_catalog[i + 1] = {'title': title, 'url': rss_url}

    with open('npr_podcasts.json', 'w') as catalog:
        json.dump(podcast_catalog, catalog, indent=4)


if __name__ == "__main__":
    get_npr_podcasts_catalog()

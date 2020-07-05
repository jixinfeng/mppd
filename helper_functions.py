import json
import requests
import string
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Tuple, NamedTuple


class ParsedEntry(NamedTuple):
    index: int
    link: str
    year: str
    date: str
    title: str
    root_path: Path
    sub_path: Path
    file_name: Path


class ParsedFeed(NamedTuple):
    author: str
    album: str
    root_path: Path
    episodes: List[ParsedEntry]


def get_valid_filename(filename: str, valid_chars=None, invalid_chars=None) -> str:
    if not valid_chars:
        valid_chars = frozenset(f"-_.() {string.ascii_letters}{string.digits}")
    valid_filename = ''.join(c for c in filename if c in valid_chars)
    return valid_filename.replace(' ', '_')


def get_rss_from_page(podcast: Tuple[str, str]) -> Tuple[str, str]:
    title, page_url = podcast
    page_html = requests.get(page_url).text
    page_soup = BeautifulSoup(page_html, 'html.parser')
    page_rss = page_soup.find('a', string='RSS link')['href']
    return title, page_rss


def get_npr_podcasts_catalog() -> None:
    catalog_url = 'https://www.npr.org/programs/'
    catalog_html = requests.get(catalog_url).text
    catalog_soup = BeautifulSoup(catalog_html, 'html.parser')
    link_block = catalog_soup.find_all('a')
    podcast_list = [
        (l.getText().strip(), l.attrs.get('href', ""))
        for l in link_block
        if l.attrs.get('href', "").startswith('https://www.npr.org/podcasts/')
    ]

    with ThreadPoolExecutor() as mt_pool:
        podcast_rss_feeds = mt_pool.map(get_rss_from_page, podcast_list)

    podcast_catalog = {}
    for i, podcast in enumerate(podcast_rss_feeds):
        title, rss_url = podcast
        podcast_catalog[i + 1] = {'title': title, 'url': rss_url}

    with open('feeds/npr_podcasts.json', 'w') as catalog:
        json.dump(podcast_catalog, catalog, indent=4)


def generate_abb_scripts(feed: ParsedFeed) -> None:
    subpaths = sorted({str(entry.sub_path) for entry in feed.episodes})
    scripts = {
        subpath: [
            f"abbinder -s -o {get_valid_filename(feed.album)}_{i}.m4b -r 22050 -b 32 -c 1 -t {feed.album} -a {feed.author}"
        ] for i, subpath in enumerate(subpaths)
    }
    for entry in feed:
        full_path = entry.root_path / entry.sub_path / entry.file_name
        title = entry.title
        scripts[str(entry.sub_path)].append(f"'@{title}@' {full_path}")
    for subpath in subpaths:
        if subpath == ".":
            script_name = Path(f"{feed.root_path}.sh")
        else:
            script_name = Path(f"{feed.root_path}_{subpath}.sh")

        with script_name.open(mode='w') as f:
            f.write(" \\\n".join(scripts[subpath]))
    return


if __name__ == "__main__":
    get_npr_podcasts_catalog()

import argparse
import feedparser
import requests
import time
import string
from collections import namedtuple
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, wait

ParsedEntry = namedtuple('ParsedEntry', ['index', 'link', 'year', 'date', 'title', 'root_path', 'sub_path', 'file_name'])
ParsedFeed = namedtuple('ParsedFeed', ['author', 'album', 'root_path', 'episodes'])


class PodcastDownloader:
    def __init__(self, rss_url, by_year, n_threads=4):
        raw_feed = feedparser.parse(rss_url)
        self.n_threads = n_threads
        self.parsed_feeds = self.parse_feed(raw_feed, by_year)
        return

    def download_all(self):
        self.parsed_feeds.root_path.mkdir(exist_ok=True)
        with ThreadPoolExecutor(self.n_threads) as mt_pool:
            _ = mt_pool.map(self.download_and_process, self.parsed_feeds.episodes)

        return

    @staticmethod
    def download_and_process(entry, write_chunk=16):
        root_path = entry.root_path
        folder_path = root_path / entry.sub_path
        if folder_path != root_path:
            folder_path.mkdir(parents=True, exist_ok=True)

        file_path = folder_path / entry.file_name
        tmp_path = file_path.with_suffix('.tmp')

        episode_link = entry.link
        if file_path.exists():
            print(f"[SKIPPING] {file_path}")
            return
        if tmp_path.exists():
            tmp_path.unlink()
        r = requests.get(episode_link, stream=True)
        print(f"[DOWNLOADING] {entry.date} {entry.title} --> {file_path}")
        with tmp_path.open(mode='wb') as tmp_file_handle:
            for chunk in r.iter_content(chunk_size=write_chunk*1024*1024):
                if chunk:
                    tmp_file_handle.write(chunk)

        tmp_path.rename(file_path)
        return

    def parse_feed(self, raw_feed, by_year=False):
        feed_info = self._get_feed_info(raw_feed)
        parsed_feed = ParsedFeed(
            author=feed_info['author'],
            album=feed_info['album'],
            root_path=feed_info['root_path'],
            episodes=[]
        )

        for index, entry in enumerate(raw_feed.entries[::-1]):
            sub_path = ""
            link = entry.links[0].href
            published = entry['published_parsed']
            year = published.tm_year
            if by_year:
                sub_path = str(year)
            date = time.strftime("%Y%m%d", published)
            title = entry['title']
            sub_path = Path(get_valid_filename(sub_path))
            filename = Path(get_valid_filename(f"{date}-{title}.mp3"))
            parsed_feed.episodes.append(ParsedEntry(
                index=index, link=link, year=year,
                date=date, title=title, root_path=parsed_feed.root_path,
                sub_path=sub_path, file_name=filename
            ))
        return parsed_feed

    @staticmethod
    def _get_feed_info(raw_feed):
        try:
            author = raw_feed.channel.author_detail.name
        except AttributeError:
            author = None

        try:
            album = raw_feed.channel.title
        except AttributeError:
            album = None

        if author:
            root_path = Path(get_valid_filename(f"{author}-{album}"))
        else:
            root_path = Path(get_valid_filename(album))

        return {"author": author, "album": album, "root_path": root_path}


def get_valid_filename(filename, valid_chars=None):
    if not valid_chars:
        valid_chars = frozenset(f"-_.() {string.ascii_letters}{string.digits}")
    valid_filename = ''.join(c for c in filename if c in valid_chars)
    return valid_filename.replace(' ', '_')


def generate_abb_scripts(feed):
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


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--rss_feed', '-r',
        metavar='rss-feed',
        type=str,
        action='store',
        help="RSS Feed of Podcast"
    )
    parser.add_argument(
        '--year',
        action='store_true',
        help="Save episodes into sub folders by publish year"
    )
    parser.add_argument(
        '--script',
        action='store_true',
        help="If selected, generate script to bind episodes into audiobook file via Audiobook Binder"
    )
    parser.add_argument(
        '--threads',
        type=int,
        default=4,
        help="Number of parallel downloads, default=4"
    )
    args = parser.parse_args()

    return args


def main(args):
    d = PodcastDownloader(
        rss_url=args.rss_feed,
        by_year=args.year,
        n_threads=args.threads
    )

    d.download_all()
    if args.script:
        generate_abb_scripts(d.parsed_feeds)


if __name__ == "__main__":
    cli_args = parse_args()
    main(cli_args)

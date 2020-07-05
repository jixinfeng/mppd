import argparse
import feedparser
import time
from typing import List
from feedparser import FeedParserDict
from helper_functions import *


class PodcastDownloader:
    def __init__(self, rss_url: str, by_year: bool, n_threads: int = 4):
        raw_feed = feedparser.parse(rss_url)
        self.n_threads = n_threads
        self.parsed_feeds = self.parse_feed(raw_feed, by_year)
        return

    def download_all(self) -> None:
        self.parsed_feeds.root_path.mkdir(exist_ok=True)
        with ThreadPoolExecutor(self.n_threads) as mt_pool:
            _ = mt_pool.map(self.download_episode, self.parsed_feeds.episodes)

        return

    @staticmethod
    def download_episode(entry: ParsedEntry, write_chunk: int = 16):
        root_path = entry.root_path
        folder_path = root_path / entry.sub_path
        if folder_path != root_path:
            folder_path.mkdir(parents=True, exist_ok=True)

        file_path = folder_path / entry.file_name
        tmp_path = file_path.with_suffix('.tmp')

        episode_link = entry.link
        if file_path.exists():
            if file_path.stat().st_size < 10 ** 6:
                file_path.unlink()
            else:
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

    def parse_feed(self, raw_feed: FeedParserDict, by_year: bool = False) -> ParsedFeed:
        feed_info = self.__get_feed_info(raw_feed)
        parsed_feed = ParsedFeed(
            author=feed_info['author'],
            album=feed_info['album'],
            root_path=feed_info['root_path'],
            episodes=[]
        )

        for index, entry in enumerate(raw_feed.entries[::-1]):
            sub_path = ""
            link = self.__get_download_url(entry.links)
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
    def __get_feed_info(raw_feed: FeedParserDict) -> dict:
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

    @staticmethod
    def __get_download_url(url_list: List[FeedParserDict]) -> str:
        for url_entry in url_list:
            if url_entry.type == "audio/mpeg":
                raw_link = url_entry.href
                if '.mp3' in raw_link:
                    return raw_link.split('.mp3')[0] + '.mp3'
                elif '.mp4' in raw_link:
                    return raw_link.split('.mp4')[0] + '.mp4'

        raise ValueError(f"No valid url found in {[entry.href for entry in url_list]}")


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
        default=1,
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

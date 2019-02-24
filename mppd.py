import argparse
import feedparser
import requests
import time
import string
import multiprocessing as mp
from pathlib import Path


class PodcastDownloader:
    valid_chars = frozenset("-_.() {}{}".format(string.ascii_letters, string.digits))

    def __init__(self, rss, by_year, per_season):
        feed = feedparser.parse(rss)
        try:
            author = feed.channel.author_detail.name
        except AttributeError:
            author = None
        album = feed.channel.title
        if author:
            self.root_path = Path("{} - {}".format(author, album))
        else:
            self.root_path = Path(album)

        self.entries = self.parse_entries(feed, by_year, per_season)
        return
    
    def download_all(self):
        self.root_path.mkdir(exist_ok=True)
        mp_pool = mp.Pool()
        for entry in self.entries:
            mp_pool.apply_async(
                func=self.download_and_process,
                args=(entry,)
            )

        mp_pool.close()
        mp_pool.join()

    @staticmethod
    def download_and_process(entry):
        print("[{}] downloading {}".format(entry['index'], entry['title']))
        root_path = entry['root_path']
        folder_path = root_path / entry['sub_path']
        if folder_path != root_path:
            folder_path.mkdir(parents=True, exist_ok=True)

        file_path = folder_path / entry['file_name']
        tmp_path = file_path.with_suffix('.tmp')

        episode_link = entry['link']
        if file_path.exists():
            print("{} exists".format(file_path))
            return
        if tmp_path.exists():
            tmp_path.unlink()
        r = requests.get(episode_link, stream=True)
        with tmp_path.open(mode='wb') as tmp_file_handle:
            for chunk in r.iter_content(chunk_size=4*1024*1024):
                if chunk:
                    tmp_file_handle.write(chunk)

        tmp_path.rename(file_path)
        return

    def parse_entries(self, feed, by_year=False, per_seasons=None):
        entries = []
        if by_year and per_seasons:
            raise ValueError("Only one of by_year or by_season should be True")
        for index, entry in enumerate(feed.entries[::-1]):
            sub_path = ""
            if per_seasons:
                sub_path = "S" + str(index // per_seasons)
            link = entry.links[0].href
            published = entry['published_parsed']
            year = published.tm_year
            if by_year:
                sub_path = str(year)
            date = time.strftime("%Y%m%d", published)
            title = entry['title']
            filename = self.valid_filename("{} - {}.mp3".format(date, title))
            entries.append({
                'index': index,
                'link': link,
                'year': year,
                'date': date,
                'title': title,
                'root_path': self.root_path,
                'sub_path': Path(sub_path),
                'file_name': Path(filename)
            })
        return entries

    @staticmethod
    def valid_filename(filename, valid_chars=valid_chars):
        return ''.join(c for c in filename if c in valid_chars)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--rss_feed', '-r',
        metavar='rss-feed',
        type=str,
        action='store',
        help="RSS Feed of podcast"
    )
    parser.add_argument(
        '--year',
        action='store_true',
        help="Save episodes into sub folders by publish year"
    )
    parser.add_argument(
        '--by_season',
        metavar='by-season',
        type=int,
        default=0,
        help="Save episodes into sub folders by seasons, with chosen number of episodes per season"
    )
    args = parser.parse_args()
    if args.year and args.by_season:
        raise ValueError("year and by_season can not be used at same time")

    return args


def main(args):
    d = PodcastDownloader(
        rss=args.rss_feed,
        by_year=args.year,
        per_season=args.by_season
    )

    d.download_all()


if __name__ == "__main__":
    cli_args = parse_args()
    main(cli_args)

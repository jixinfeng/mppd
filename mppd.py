import argparse
import feedparser
import requests
import time
import string
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, wait


class PodcastDownloader:
    valid_chars = frozenset("-_.() {}{}".format(string.ascii_letters, string.digits))

    def __init__(self, rss, by_year, n_threads=4):
        feed = feedparser.parse(rss)
        self.n_threads = n_threads
        try:
            self.author = feed.channel.author_detail.name
        except AttributeError:
            self.author = None
        self.album = feed.channel.title
        if self.author:
            self.root_path = Path(self.valid_filename("{}-{}".format(self.author, self.album)))
        else:
            self.root_path = Path(self.valid_filename(self.album))

        self.entries = self.parse_entries(feed, by_year)
        return
    
    def download_all(self):
        self.root_path.mkdir(exist_ok=True)
        with ThreadPoolExecutor(self.n_threads) as mt_pool:
            _ = mt_pool.map(self.download_and_process, self.entries)

    def generate_abb_scripts(self):
        subpaths = sorted({str(entry['sub_path']) for entry in self.entries})
        scripts = {
            subpath: ["abbinder -s -o {}_{}.m4b -r 22050 -b 32 -c 1 -t {} -a {}".format(
                self.valid_filename(self.album), i, self.album, self.author
            )] for i, subpath in enumerate(subpaths)}
        for entry in self.entries:
            full_path = entry['root_path'] / entry['sub_path'] / entry['file_name']
            title = entry['title']
            scripts[str(entry['sub_path'])].append(
                "'@{}@' {}".format(title, full_path)
            )
        for subpath in subpaths:
            if subpath == ".":
                script_name = Path("{}.sh".format(self.root_path))
            else:
                script_name = Path("{}_{}.sh".format(self.root_path, subpath))

            with script_name.open(mode='w') as f:
                f.write(" \\\n".join(scripts[subpath]))

    @staticmethod
    def download_and_process(entry):
        root_path = entry['root_path']
        folder_path = root_path / entry['sub_path']
        if folder_path != root_path:
            folder_path.mkdir(parents=True, exist_ok=True)

        file_path = folder_path / entry['file_name']
        tmp_path = file_path.with_suffix('.tmp')

        episode_link = entry['link']
        if file_path.exists():
            print("[SKIPPING] {}".format(file_path))
            return
        if tmp_path.exists():
            tmp_path.unlink()
        r = requests.get(episode_link, stream=True)
        print("[DOWNLOADING] {} {} --> {}".format(
            entry['date'],
            entry['title'],
            file_path
        ))
        with tmp_path.open(mode='wb') as tmp_file_handle:
            for chunk in r.iter_content(chunk_size=16*1024*1024):
                if chunk:
                    tmp_file_handle.write(chunk)

        tmp_path.rename(file_path)
        return

    def parse_entries(self, feed, by_year=False):
        entries = []
        for index, entry in enumerate(feed.entries[::-1]):
            sub_path = ""
            link = entry.links[0].href
            published = entry['published_parsed']
            year = published.tm_year
            if by_year:
                sub_path = str(year)
            date = time.strftime("%Y%m%d", published)
            title = entry['title']
            sub_path = self.valid_filename(sub_path)
            filename = self.valid_filename("{}-{}.mp3".format(date, title))
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
        valid_filename = ''.join(c for c in filename if c in valid_chars)
        return valid_filename.replace(' ', '_')


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
        rss=args.rss_feed,
        by_year=args.year,
    )

    d.download_all()
    if args.script:
        d.generate_abb_scripts()


if __name__ == "__main__":
    cli_args = parse_args()
    main(cli_args)

import argparse
import feedparser
import pathlib
import requests
import time
import string


class PodcastDownloader:
    valid_chars = frozenset("-_.() {}{}".format(string.ascii_letters, string.digits))

    def __init__(self, rss):
        feed = feedparser.parse(rss)
        self.author = feed.channel.author_detail.name
        self.album = feed.channel.title
        self.entries = self.parse_entries(feed)
        self.dir_name = pathlib.Path("{} - {}".format(self.author, self.album))
        return
    
    def download_all(self):
        self.dir_name.mkdir(exist_ok=True)
        for entry in self.entries:
            self.download_and_process(entry)
        
    def download_and_process(self, entry):
        print("[{}] downloading {}".format(entry['index'], entry['title']))
        file_path = self.dir_name / entry['file_name']
        tmp_path = file_path.with_suffix('.tmp')
        episode_link = entry['link']
        if file_path.exists():
            print("{} exists".format(file_path))
            return
        if tmp_path.exists():
            tmp_path.unlink()
        self.download_episode(episode_link, tmp_path)
        tmp_path.rename(file_path)
        return

    def parse_entries(self, feed):
        entries = []
        for index, entry in enumerate(feed.entries):
            link = entry.links[0].href
            published = entry['published_parsed']
            year = published.tm_year
            date = time.strftime("%Y%m%d", published)
            title = entry['title']
            filename = self.valid_filename("{} - {}.mp3".format(date, title))
            entries.append({
                'index': index,
                'link': link,
                'year': year,
                'date': date,
                'title': title,
                'file_name': filename
            })
        return entries

    @staticmethod
    def download_episode(link, file_path):
        r = requests.get(link, stream=True) 
        with file_path.open(mode='wb') as f:
            for chunk in r.iter_content(chunk_size=4*1024*1024): 
                if chunk: 
                    f.write(chunk) 
        return

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
    args = parser.parse_args()

    return args


def main(args):
    d = PodcastDownloader(
        rss=args.rss_feed
    )

    d.download_all()


if __name__ == "__main__":
    cli_args = parse_args()
    main(cli_args)

import argparse
import feedparser
import pathlib
import requests
import time
from mp3_tagger import MP3File
import string


class PodcastDownloader:
    def __init__(self, rss, artist, album):
        self.feed = feedparser.parse(rss)
        self.album_info = dict()
        self.album_info['artist'] = artist
        self.album_info['album'] = album
        self.dir_name = pathlib.Path("{} - {}".format(artist, album))
        self.valid_chars = set("-_.() {}{}".format(string.ascii_letters, string.digits))
        return
    
    def download_all(self, n=None, reverse=False):
        if n <= 0:
            n = 1
        if n > len(self.feed.entries):
            n = len(self.feed.entries)
        queue = []
        if reverse:
            for entry in self.feed.entries[::-1][:n]:
                queue.append(self.entry_to_dict(entry))
        else:
            for entry in self.feed.entries[:n]:
                queue.append(self.entry_to_dict(entry))

        self.dir_name.mkdir(exist_ok=True)
        for i, q in enumerate(queue):
            print("[{}]".format(i), end='')
            self.download_and_process(q)
        
    def download_and_process(self, entry):
        print("downloading {}".format(entry['title']))
        old_name_path = self.dir_name / entry['old_name']
        new_name_path = self.dir_name / entry['new_name']
        episode_link = entry['link']
        if new_name_path.exists():
            print("{} exists".format(new_name_path))
            return
        if old_name_path.exists():
            old_name_path.unlink()
        self.download_episode(episode_link, old_name_path)
        self.update_tags(old_name_path, {**entry, **self.album_info})
        old_name_path.rename(new_name_path)
        return
        
    def entry_to_dict(self, entry):
        link = entry['link']
        filename = link.split('/')[-1].split('?')[0]
        if '.' in filename:
            ext_name = filename.split('.')[-1]
        else:
            ext_name = "mp3"
        date = time.strftime("%Y%m%d", entry['published_parsed'])
        title = entry['title']
        return {
            'link': link,
            'date': date,
            'title': title,
            'old_name': filename,
            'new_name': self.valid_filename("{} - {}.{}".format(date, title, ext_name))
        }
    
    @staticmethod
    def download_episode(link, file_path):
        r = requests.get(link, stream=True) 
        with file_path.open(mode='wb') as f:
            for chunk in r.iter_content(chunk_size=4*1024*1024): 
                if chunk: 
                    f.write(chunk) 
        return True
    
    @staticmethod
    def update_tags(file_path, tags):
        file = MP3File(str(file_path))
        file.album = tags['album']
        file.artist = tags['artist']
        file.song = tags['title']
        file.save()
        return True
    
    def valid_filename(self, filename):
        return ''.join(c for c in filename if c in self.valid_chars)


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
        '--episodes', '-n',
        type=int,
        default=1,
        action='store',
        help="number of episodes to be downloaded, default 1"
    )
    parser.add_argument(
        '--reverse',
        action='store_true',
        help="download from the oldest episode, selected by default"
    )
    parser.add_argument(
        '--artist', '-a',
        type=str,
        help="artist of podcast"
    )
    parser.add_argument(
        '--album_title', '-t',
        metavar='album-title',
        type=str,
        help="album title of podcast"
    )
    args = parser.parse_args()
    parser.set_defaults(reverse=False)
    if args.episodes <= 0:
        parser.error("--episode must be bigger than 0")

    return args


def main(args):
    d = PodcastDownloader(
        rss=args.rss_feed,
        artist=args.artist,
        album=args.album_title
    )

    d.download_all(
        n=args.episodes,
        reverse=args.reverse
    )


if __name__ == "__main__":
    cli_args = parse_args()
    main(cli_args)

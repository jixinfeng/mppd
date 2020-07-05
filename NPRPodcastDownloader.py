from PodcastDownloader import *
from helper_functions import *


class NPRPodcastDownloader(PodcastDownloader):
    def __init__(self, rss_url: str, get_transcript: bool = True, by_year: bool = True):
        super().__init__(rss_url=rss_url, by_year=by_year)
        self.get_transcript = get_transcript

    def download_episode(self, entry: ParsedEntry, write_chunk: int = 16):
        super().download_episode(entry, write_chunk)

        if self.get_transcript:
            transcript_path = entry.root_path / entry.sub_path / entry.file_name.with_suffix('.txt')
            tmp_path = transcript_path.with_suffix('.tmp')
            if transcript_path.exists():
                return
            if tmp_path.exists():
                tmp_path.unlink()

            story_id = entry.link.split('/')[-2]
            transcript_url = f"https://www.npr.org/templates/transcript/transcript.php?storyId={story_id}"
            transcript_page_html = requests.get(transcript_url).text
            soup = BeautifulSoup(transcript_page_html, 'html.parser')
            transcript_block = soup.find_all('div', attrs={'class': 'transcript storytext'})[0]
            transcript_text = '\n'.join(list(map(lambda l: l.getText(), transcript_block.find_all('p'))))

            with tmp_path.open(mode='w') as tmp_transcript_handle:
                tmp_transcript_handle.write(transcript_text)

            tmp_path.rename(transcript_path)
            return


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--program', '-p',
        type=str,
        action='store',
        default=None,
        help="Choosing program by its id"
    )
    parser.add_argument(
        '--rss_feed', '-r',
        metavar='rss-feed',
        type=str,
        action='store',
        default=None,
        help="RSS Feed of Podcast, this overrides --program, leave both blank to choose manually"
    )
    args = parser.parse_args()

    return args


def main(args):
    with open('feeds/npr_podcasts.json', 'r') as catalog:
        podcasts = json.load(catalog)

    catalog_prompt = "\nPick a podcast by number: "
    catalog_message = "\n".join([f"{i}: {podcast['title']}" for i, podcast in podcasts.items()]) + catalog_prompt
    if args.rss_feed:
        valid_rss = {p["url"] for _, p in podcasts.items()}
        if args.rss_feed not in valid_rss:
            raise ValueError("Invalid RSS Feed")
        else:
            rss_feed = args.rss_feed
    elif args.program:
        if args.program not in podcasts:
            raise ValueError("Invalid Program id")
        else:
            rss_feed = podcasts[args.program]['url']
    else:
        print(catalog_message, end="")
        program = input()
        while program not in podcasts:
            print(catalog_message, end="")
            program = input()

        rss_feed = podcasts[args.program]['url']

    d = NPRPodcastDownloader(rss_url=rss_feed)
    d.download_all()


if __name__ == "__main__":
    cli_args = parse_args()
    main(cli_args)

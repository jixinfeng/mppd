import json
from bs4 import BeautifulSoup
from PodcastDownloader import *


class NPRPodcastDownloader(PodcastDownloader):
    def __init__(self, rss_url, get_transcript=True):
        super().__init__(rss_url=rss_url, by_year=True)
        self.get_transcript = get_transcript

    def download_episode(self, entry, write_chunk=16):
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
        help="Choosing program by its id, leave blank to see the full list"
    )
    args = parser.parse_args()

    return args


def main(args):
    with open('npr_podcasts.json', 'r') as catalog:
        podcasts = json.load(catalog)

    catalog_prompt = "\nPick a podcast by number: "
    catalog_message = "\n".join([f"{i}: {podcast['title']}" for i, podcast in podcasts.items()]) + catalog_prompt
    if not args.program:
        print(catalog_message, end="")
        program = input()
        while program not in podcasts.keys():
            print(catalog_message, end="")
            program = input()
    else:
        program = args.program

    rss_feed = podcasts[program]['url']
    d = NPRPodcastDownloader(rss_url=rss_feed)
    d.download_all()


if __name__ == "__main__":
    cli_args = parse_args()
    main(cli_args)

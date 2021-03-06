import os
import argparse
import json
import sys
import re
import requests
from json import JSONEncoder
from bs4 import BeautifulSoup


class Song:
    def __init__(self, title: str, artist: str, album: str, release: str, lyrics: str, url: str):
        self.title = title
        self.artist = artist
        self.album = album
        self.release = release
        self.lyrics = lyrics
        self.url = url


class SongEncoder(JSONEncoder):
    def default(self, o):
        return o.__dict__


class SearchResult:
    def __init__(self, result):
        result =  result['result']
        self.link = result['url'].encode('ascii', 'ignore').decode("utf-8")
        self.title = result['title'].encode('ascii', 'ignore').decode("utf-8")
        self.artist = result['primary_artist']['name'].encode('ascii', 'ignore').decode("utf-8")

    def __str__(self):
        return f'{self.title} by {self.artist}'


def eprint(*args, **kwargs):
    """
    Print the given message to stderr
    """
    print(*args, file=sys.stderr, **kwargs)


def search(term: str) -> str:
    """
    Search for a term
    """
    original_term = term
    term = re.sub('[^a-zA-Z0-9 ]+', '', term).strip()
    term = re.sub(' ', '+', term)
    search_page = requests.get(f'https://genius.com/api/search/song?page=1&q={term}')
    if search_page.status_code != 200:
        eprint(f'Status code {search_page.status_code} for search term "{original_term}" indicates failure')
        return None
    parsed_page = json.loads(search_page.text)
    search_results = parsed_page['response']['sections'][0]['hits']
    results = [SearchResult(result) for result in search_results]
    if len(results) == 0:
        eprint(f'No songs found for query {original_term}')
        sys.exit(1)
    if len(results) is 1:
        print(f'Only result found is {results[0]}')
        return results[0].link
    for num in range(1, min(16, len(results)+1)):
        print(f'{num}. {results[num-1]}')
    result = results[int(input('Select a number: '))-1]
    return result.link


def download_url(url: str):
    """
    Retrieve the page contents and parse out the lyrics from a given url
    """
    if not url.startswith('https://genius.com/'):
        eprint(f'URL "{url}" does not appear to be a valid genius lyrics url')
        return None
    result = requests.get(url)
    if result.status_code != 200:
        eprint(f'Status code {result.status_code} for url "{url}" indicates failure')
        return None
    parsed_page = BeautifulSoup(result.text.replace(u"\u2018", "'").replace(u"\u2019", "'"), 'html.parser')
    song_lyrics = parsed_page.find_all('div', attrs={'class': 'lyrics'})[0].text.strip()
    song_data = json.loads([line for line in result.text.split('\n') if 'TRACKING_DATA' in line][0].split('=')[1].strip(' ;'))
    song_artist = song_data['Primary Artist'].encode('ascii', 'ignore').decode("utf-8")
    song_title = song_data['Title'].encode('ascii', 'ignore').decode("utf-8")
    song_album = (song_data['Primary Album'] if song_data['Primary Album'] is not None else 'Unknown Album').encode('ascii', 'ignore').decode("utf-8")
    song_release = song_data['Release Date'].encode('ascii', 'ignore').decode("utf-8")
    song = Song(title=song_title, artist=song_artist, album=song_album, lyrics=song_lyrics, url=url, release=song_release)
    return song


def save_to_file(song: Song):
    filename = './lyrics/genius_'
    for c in song.title.lower():
        if c.isalpha() or c.isdigit():
            filename = filename + c
        if c is ' ':
            filename = filename + '-'
    filename = filename + '_'
    for c in song.artist.lower():
        if c.isalpha() or c.isdigit():
            filename = filename + c
        if c is ' ':
            filename = filename + '-'
    filename = filename + '.json'
    if not os.path.isdir('./lyrics'):
        os.mkdir('./lyrics')
    f = open(filename, 'w')
    json.dump(song, f, indent=4, cls=SongEncoder)
    f.close()
    print('Lyrics saved to ' + filename)


def main():
    parser = argparse.ArgumentParser(description='Scraper for lyrics from genius.com')
    parser.add_argument('term', metavar='TERM', help='Term to search for', nargs='+')
    parser.add_argument('--no-save', help='Whether or not to save the data to a file', action='store_false')
    args = parser.parse_args()

    if args.term is not None:
        term = ' '.join(args.term)
        if term.startswith('https://genius.com/'):
            song = download_url(term)
        else:
            song = download_url(search(term))
        if args.no_save:
            save_to_file(song)
        else:
            print('Title: ' + song.title)
            print('Artist: ' + song.artist)
            print('Album: ' + song.album + '\n')
            print(song.lyrics)
    else:
        eprint('No URL given, doing nothing')



if __name__ == '__main__':
    main()

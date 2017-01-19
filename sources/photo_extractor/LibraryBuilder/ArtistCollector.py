from lxml import etree
import os.path
import re

""" ArtistCollector v0.0.2
    author - lila ramharter <lila.ramharter@technikum-wien.at>
    info   - Parses xml music library file and gets all artist names
             The xml file is NOT included in the git repo, because it it pretty big.
"""


class ArtistCollector:
    """ ArtistCollector parses an xml representation of a foobar2000 playlist file """
    def __init__(self, file='playlist.xml'):
        self.filename = file
        if not os.path.exists(self.filename):
            print("Playlist file not found. Locate your file.")

    def collect_artists(self):
        """ Parse file for artist names """
        if not os.path.exists(self.filename):
            print("Could not collect artists: File not found")
            return

        parser = etree.XMLParser(remove_blank_text=True)
        with open(self.filename, 'r', encoding='utf-8') as f:
            try:
                tree = etree.parse(f, parser).getroot()
            except Exception as e:
                print(str(e))
                raise

        artists = []
        for entry in tree.xpath(".//artist"):
            name = entry.text.strip(' ')
            # remove problematic characters
            name = re.sub('["/\'!-]', '', name)
            if name.lower() not in artists:
                artists.append(name.lower())

        print(len(artists), 'artists found.')
        return artists

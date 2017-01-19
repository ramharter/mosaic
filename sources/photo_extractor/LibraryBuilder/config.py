import json
import logging
import urllib.request
import urllib.parse
import os.path
from lxml import etree
from PIL import Image

from ArtistCollector import *

__author__ = 'Lila Ramharter'
__email__ = 'lila.ramharter@technikum-wien.at'
__version__ = '0.25.0'
__license__ = "Do whatever you want but no evil stuff."

""" TO DO:
        - add headers for fanart.tv, so they don't wonder who i am when retrieving images
"""


class Config:
    """ Config class contains program-wide configurations """
    def __init__(self):

        self.appname = 'LibraryBuilder'
        self.version = __version__
        self.author = __author__
        self.contact = __email__
        self.filename = 'ImageLibrary.xml'

        # header sent to musicbrainz for identification
        self.headers = {'User-Agent': self.appname + '/' + self.version + ' ( ' + self.contact + ' )'}

        # API key for fanart.tv
        self.api_key = '2bd7429bab36fa40ec43932d6f989925'

        # enable logging to file
        logging.basicConfig(handlers=[logging.FileHandler('log.txt', 'a', 'UTF-8')],
                            level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

    def set_headers(self, headers):
        """
        Change headers sent to Musicbrainz
        :param headers: new headers. must be a dictionary
        """
        if isinstance(headers, dict):
            self.headers = headers
        else:
            logging.error('Config.set_headers: Headers must be dict')




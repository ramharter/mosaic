from config import *
import Cluster


class Library:
    """
    Library class contains all methods used in the creation of an image database.
    """
    def __init__(self):
        """ Initialize Library """
        self.config = Config()
        # load existing library from file or create new library
        if os.path.isfile(self.config.filename):
            self.load_etree(self.config.filename)
        else:
            self.lib_tree = etree.Element('root')

    def add_artist(self, artist=None, id=None):
        """
        Add artist to library etree from artist name or MBID (Musicbrainz ID)
        :param artist: name of artist
        :param id: MBID of artist
        """
        if artist is None and id is None:
            logging.error("library.add_artist: Need artist name or MBID")
            return
        elif id is None:
            # check if artist name is already in library to avoid calling musicbrainz for nothing
            if self.lib_tree.find(".//artist[@name='" + artist + "']") is not None:
                logging.debug('Artist already in library: %s', artist)
                return
            id = self.get_artist_id(artist)
            if id is None:
                logging.debug("Could not retrieve artist id from database: %s", artist)
                return
            name = artist
        elif artist is None:
            # check if artist id is already in library to avoid calling musicbrainz for nothing
            if self.lib_tree.find(".//artist[@id='" + id + "']") is not None:
                logging.debug('Artist already in library: %s', id)
                return
            name = self.get_artist_name(id)
            if name is None:
                logging.debug("Could not retrieve artist name from database: %s", id)
                return

        # check one final time if artist is in library
        if self.lib_tree.find(".//artist[@id='" + id + "']") is not None:
            logging.debug('Artist already in library: %s, %s', name, id)
            return

        # get album covers for artist
        covers = self.get_album_cover_urls(id)

        # if there are any album covers found for this artist, add artist to library
        if len(covers):
            logging.debug("%d album covers found for artist %s", len(covers), name)
            artist_element = etree.SubElement(self.lib_tree, 'artist', name=name.lower(), id=id)
            for cover in covers:
                etree.SubElement(artist_element, 'album', url=cover)
        else:
            logging.debug("No album covers found for artist %s", name)

    def write_etree(self, filename='ImageLibrary.xml'):
        """ Write xml tree to file. If no filename specified, will write to 'ImageLibrary.xml' in source folder """
        if len(self.lib_tree):
            with open(filename, 'w') as f:
                # use .decode because etree.tostring returns bytes for some reason
                f.write(etree.tostring(self.lib_tree, pretty_print=True).decode('utf-8'))
        else:
            logging.error('library.write_etree: Library is empty, nothing to write.')

    def load_etree(self, filename):
        """ Load library from xml file """
        if not os.path.isfile(filename):
            logging.error('File not found: ' + filename)
            return None

        # add parser to avoid pretty-print problems on parsed data
        parser = etree.XMLParser(remove_blank_text=True)
        with open(filename, 'r') as f:
            try:
                library_tree = etree.parse(f, parser).getroot()
            except Exception as e:
                logging.error(str(e))
                raise

        self.lib_tree = library_tree

    def get_artist_id(self, name):
        """ Get artist MBID from name """

        # Piece together url from artist name (in case it look like 'the-smiths')
        artist_string = urllib.parse.quote('-'.join(name.split(' ')))
        url = 'http://musicbrainz.org/ws/2/recording/?query=artist:' + str(artist_string)
        logging.debug('Trying: ' + url)

        # get artist data from Musicbrainz webservice (returns xml)
        req = urllib.request.Request(url, headers=self.config.headers)
        parser = etree.XMLParser(remove_blank_text=True)
        try:
            page_tree = etree.parse(urllib.request.urlopen(req), parser=parser).getroot()
        except urllib.error.HTTPError as e:
            logging.error(e)
            return None

        # TODO: find a way to get namespace from file instead of hard-coding it
        # artist = page_tree.find(".//artist", namespaces=page_tree.nsmap) does not work?
        artist = page_tree.find(".//{http://musicbrainz.org/ns/mmd-2.0#}artist")
        if artist is None:
            logging.error('library.get_artist_id: No artist found.')
            return None

        return artist.get('id')

    def get_artist_name(self, id):
        """ Get artist name from MBID """
        url = 'http://musicbrainz.org/ws/2/artist/?query=arid:' + id
        logging.debug('Trying: ' + url)

        # get artist data from Musicbrainz webservice
        req = urllib.request.Request(url, headers=self.config.headers)
        parser = etree.XMLParser(remove_blank_text=True)
        try:
            page_tree = etree.parse(urllib.request.urlopen(req), parser=parser).getroot()
        except urllib.error.HTTPError as e:
            logging.error(e)
            return None

        # TODO: find a way to get namespace from file instead of hard-coding it
        try:
            artist_name = page_tree.find(".//{http://musicbrainz.org/ns/mmd-2.0#}sort-name").text
        except AttributeError:
            logging.error('library.get_artist_name: No artist found for id %s.', id)
            return None

        return artist_name

    def get_album_cover_urls(self, id):
        """ get urls to all album cover art available for specific artist id on fanart.tv """
        covers = []
        url = 'http://webservice.fanart.tv/v3/music/' + id + '?api_key=' + self.config.api_key
        logging.debug("Trying url: " + url)

        try:
            response = urllib.request.urlopen(url).read().decode('utf-8')
        except urllib.error.HTTPError as e:
            logging.error('library.get_album_cover_urls: ' + str(e))
            return []

        # fanart API returns json. get data from json structure
        json_data = json.loads(response)
        try:
            albums = json_data['albums']
        except KeyError:
            logging.error('library.get_album_covers: No covers found. ')
            return []

        for album in albums:
            try:
                covers.append(albums[album]['albumcover'][0]['url'])
            except KeyError:
                logging.error("Album without cover found. Ignoring.")
                continue
        return covers

    def get_number_of_entries(self):
        """ Get number of entries ( = artists) in library """
        return len(self.lib_tree)

    def get_number_of_albums(self):
        """ Get number of album covers in library """
        albums = 0
        for entry in self.lib_tree.getchildren():
            albums += len(entry)
        return albums

    def save_images_to_folder(self, folder):
        """ Save all album covers in database to a specified location on disk """
        # create base directory
        if not os.path.exists(folder):
            os.makedirs(folder)
            logging.debug("Created directory " + folder)

        for entry in self.lib_tree.getchildren():
            i = 0

            # iterate through album covers and save to disk if they have not been saved before
            for album in entry.getchildren():
                i += 1
                if album.get('path') is None or folder not in album.get('path'):
                    try:
                        image_path, headers = urllib.request.urlretrieve(album.get('url'))
                    except urllib.error.HTTPError as e:
                        logging.error("library.save_images_to_folder: " + str(e))
                        continue

                    image = Image.open(image_path)
                    # check whether image is cmyc or rgb and convert if necessary (cmyc cannot be saved as png)
                    if not image.mode == 'RGB':
                        image = image.convert('RGB')

                    # remove all problematic characters from artist name and save image to folder
                    name = entry.get('name').replace("'", '').replace(',', '').replace('?', '').strip(' ')
                    name = '-'.join(name.split(' '))
                    path = os.path.join(folder, "%s-%s.png" % (name, i))
                    image.save(path)
                    album.set('path', path)
                    logging.debug("Album cover saved to " + path)

                    # remove temp file
                    os.remove(image_path)

    def get_latest_artists(self):
        """ get latest artists from fanart.tv
            to bring a bit of randomness to the database """
        url = 'http://webservice.fanart.tv/v3/music/latest' + '?api_key=' + self.config.api_key
        try:
            response = urllib.request.urlopen(url).read().decode('utf-8')
        except urllib.error.HTTPError as e:
            logging.error('library.get_latest_artists: ' + str(e))
            return

        artists = []
        # parse json and add all artists to library
        try:
            json_data = json.loads(response)
            for entry in json_data:
                # remove problematic characters
                name = entry['name'].replace("'", '').replace(',', '').replace('?', '').strip(' ')
                self.add_artist(artist=name)
        except (json.decoder.JSONDecodeError, KeyError):
            logging.error('library.get_latest_artists: Error reading JSON response from fanart.tv ')

    def get_quad_colors(self):
        """ Get prominent color for each quadrant of the image and write to database as q0 to q3 """
        for artist in self.lib_tree.getchildren():
            for album in artist.getchildren():
                if album.get('q0') is None:
                    # if no color values exist for this album
                    quads = self.get_quadrants(Image.open(album.get('path')))
                    for i, quad in enumerate(quads):
                        q = list(Cluster.colorz2(quad, n=1))
                        name = 'q' + str(i)
                        album.set(name, q[0])
                    logging.debug("Colors got from %s: %s, %s, %s, %s" % (album.get('path'), album.get('q0'),
                                                                          album.get('q1'), album.get('q2'),
                                                                          album.get('q3')))

    def get_quadrants(self, tile):
        """
        Split image into four pieces and return a list of them
        :param tile: the image to be split
        :return: a list of quadrants
        """
        imwidth, imheight = tile.size
        width = imwidth // 2
        height = imheight // 2

        quad = []
        for i in range(imheight // height):
            for j in range(imwidth // width):
                box = (j * width, i * height, (j + 1) * width, (i + 1) * height)
                q = tile.crop(box)
                quad.append(q)
        return quad

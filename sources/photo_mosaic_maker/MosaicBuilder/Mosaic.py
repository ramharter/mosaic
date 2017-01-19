import os
import logging
import time
import math
from PIL import Image
from multiprocessing import Pool
from lxml import etree
import Cluster

# initiate logging
logger = logging.getLogger(__name__)
handler = logging.FileHandler('./log.txt', 'a', 'UTF-8')
formatter = logging.Formatter('%(asctime)s - %(levelname)s\t - %(process)s\t - %(name)s\t - %(funcName)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

MAX_DIFF = 150  # maximal euclidean difference of a match


class Mosaic:
    """
    Mosaic prepares data and starts individual worker processes
    """
    def __init__(self, input_path, output_path=None,
                 database="../../photo_extractor/LibraryBuilder/MusicLibrary.xml",
                 db_path="J:\\Mosaic\\database\\", tile_size=200, tile_divider=100):
        """
        Initialize data and create mosaic image
        :param input_path: path to input image
        :param output_path: path to output image or None for default location (./[input image]_result.jpg)
        :param database: path to xml library file
        :param db_path: path to local image database
        :param tile_size: desired size per tile in output image in px
        :param tile_divider: determines amount of tiles / detail of output image (100 - 200 recommended)
        """
        # initiate logging
        # self.logger = logging.getLogger('Mosaic')
        # handler = logging.FileHandler('./log.txt', 'w', 'UTF-8')
        # formatter = logging.Formatter(
        #     '%(asctime)s - %(levelname)s\t - %(process)s\t - %(name)s\t - %(funcName)s: %(message)s')
        # handler.setFormatter(formatter)
        # self.logger.addHandler(handler)
        # self.logger.setLevel(logging.DEBUG)

        # determine start time (used later to display total runtime)
        self.start_time = time.time()

        # check params, making sure that multiple errors can be detected and communicated to the user
        error = False
        if not os.path.isfile(input_path):
            logger.critical("Image path not found at %s " % input_path)
            print("Error: Original image file not found at %s." % input_path)
            error = True
        if not os.path.isfile(database):
            logger.critical('Database file not found at %s' % database)
            print("Error: database file not found at %s." % database)
            error = True
        if not os.path.exists(db_path):
            logger.critical('Image database not found at %s' % db_path)
            print("Error: Image database not found at %s." % db_path)
            error = True
        if error:
            print("Exiting...")
            exit(-1)

        # load original image
        try:
            self.original_image = Image.open(input_path)
        except IOError as e:
            logger.error(str(e))
            print(e)
            exit(-1)

        # if not output path is specified, set output path to '[input image name]_result.jpg' in local folder
        if output_path is None:
            self.output_path = './' + input_path.split('/')[-1].split('.')[0] + '_result.jpg'
        else:
            self.output_path = output_path
        logger.info('Resulting image will be saved to %s' % self.output_path)

        self.lib_path = database
        self.db_path = db_path
        self.crop_size = self.get_crop_size(tile_divider)
        self.tile_size = tile_size
        self.tilesX, self.tilesY = self.get_tile_number()

        # try to create output image (64bit python is your new best friend)
        try:
            self.result = Image.new('RGB', self.get_output_size())
        except MemoryError:
            logger.critical("Failed to create output image with %d/%d px. Try again with smaller tile size."
                            % self.get_output_size())
            exit(-1)
        else:
            logger.info("Created output image with %d/%d px" % self.get_output_size())

        # start mosaic creation
        self.start()

        # determine total run time
        duration = time.time() - self.start_time
        print("Finished after %d:%d minutes" % (duration // 60, duration % 60))
        logger.info("Finished after %d:%d minutes" % (duration // 60, duration % 60))

    def start(self):
        """
        Split original image into four quadrants, start worker process for each quadrant,
        assemble the resulting output image, and save to output path
        """
        logger.info('Starting mosaic creation')
        quadrants = self.get_quadrants()
        paths = self.save_images(quadrants)

        # start pool of worker processes and wait until they finish
        pool = Pool(processes=4)
        results = pool.map(self.run, paths)
        pool.close()
        pool.join()
        logger.info("Mosaic quadrants finished. Starting to assemble output.")
        print("Finishing...")

        # combine the four mosaics into the final output image and save result to output_path
        self.combine_quadrants(results)
        self.result.save(self.output_path)
        logger.info("Result saved to %s" % self.output_path)
        print("Result saved to %s" % self.output_path)

        # cleanup
        for path in paths:
            os.remove(path)

    def run(self, im_path):
        """
        Start Worker with all needed parameters and create mosaic from image at im_path
        :param im_path: path to the image
        :return: the mosaic created by the worker
        """
        m = Worker(input_path=im_path, database=self.lib_path, db_path=self.db_path,
                   crop_size=self.crop_size, tile_size=self.tile_size)
        m.mosaic()
        return m.result

    def get_quadrants(self):
        """
        Split image into 4 quadrants while ensuring that each can fit an integer amount of tiles.

        To ensure that the quadrant-mosaics can be combined again into one large mosaic, each quadrant must fit an
        integer amount of tiles. So in case the amount of tiles in the horizontal or vertical direction is not even,
        we have to make one quadrant slightly smaller and the other one slightly larger.
        e.g. 76 and 77 instead of 76.5 for both.
        :return: a list of images
        """
        w = []
        h = []
        quad = []

        # calculate widths and heights of quadrants
        w.append((self.tilesX // 2) * self.crop_size)
        w.append(w[0] if self.tilesX % 2 == 0 else (self.tilesX - (self.tilesX // 2)) * self.crop_size)

        h.append((self.tilesY // 2) * self.crop_size)
        h.append(h[0] if self.tilesY % 2 == 0 else (self.tilesY - (self.tilesY // 2)) * self.crop_size)

        # this is some brainfuck.
        # you could also write it like this:
        # start = 0
        # middleX = w[0]
        # middleY = h[0]
        # endX = w[0] + w[1]
        # endY = h[0] + h[1]
        # box0 = (start, start, middleX, middleY)
        # box1 = (middleX, start, endX, middleY)
        # box2 = (start, middleY, middleX, endY)
        # box3 = (middleX, middleY, endX, endY)

        for i in range(2):      # y-axis
            for j in range(2):  # x-axis
                box = (0 if j == 0 else w[j-1], 0 if i == 0 else h[i-1],
                       w[j] if j == 0 else w[j] + w[j-1], h[i] if i == 0 else h[i] + h[i-1])
                q = self.original_image.crop(box)
                quad.append(q)
        return quad

    def combine_quadrants(self, quads):
        """
        Combine four quadrants into one image
        :param quads: a list of quadrants in order  0, 1
                                                    2, 3
        """
        for i in range(2):
            for j in range(2):
                # determine quadrant number (0, 1, 2, or 3)
                no = (i * 2) + j
                quad = quads[no]

                # determine start- and endpoint on x-axis
                if no in [0, 2]:
                    w1 = 0
                    w2 = quad.size[0]
                else:
                    w1 = quads[no-1].size[0]
                    w2 = w1 + quad.size[0]

                # determine start- and endpoint on y-axis
                if no in [0, 1]:
                    h1 = 0
                    h2 = quad.size[1]
                else:
                    h1 = quads[no-2].size[1]
                    h2 = h1 + quad.size[1]

                box = (w1, h1, w2, h2)
                self.result.paste(im=quad, box=box)

    def save_images(self, images):
        """
        Save images to tmp folder (create directory if it does not exist) in working dir
        :param images: the images to be saved
        :return: paths to saved images
        """
        paths = []
        # create base directory
        if not os.path.exists('./tmp'):
            os.makedirs('./tmp')

        # save all images
        for i, tile in enumerate(images):
            path = os.path.join('./tmp', "img-%s.bmp" % i)
            tile.save(path)
            paths.append(path)
        return paths

    def get_imsize(self):
        """
        Get original image size
        :return: original image width and height as tuple
        """
        return self.original_image.size

    def get_output_size(self):
        """
        Determine output image size depending on tile size
        :return: size of resulting image as tuple
        """
        return self.tile_size * self.tilesX, self.tile_size * self.tilesY

    def get_crop_size(self, tile_divider):
        """
        Determine tile size depending on image proportions
        :param tile_divider: desired number of tiles on longer edge
        :return: size of on side of crop box
        """
        w, h = self.get_imsize()

        # divide the larger side of the image by tile_divider
        crop_size = w // tile_divider if w >= h else h // tile_divider

        # minimal cropsize = 2 px
        if crop_size < 2:
            crop_size = 2
        logger.debug('Cropsize determined as %d px' % crop_size)
        return crop_size

    def get_tile_number(self):
        """
        Return amount of horizontal and vertical tiles depending on crop_size
        :return: amount of tiles horizontal and vertical"""
        w, h = self.original_image.size
        return w // self.crop_size, h // self.crop_size


class Worker:
    """
    Worker creates a mosaic based on the input image from tiles in the local database
    """
    def __init__(self, input_path, crop_size,
                 database="../../photo_extractor/LibraryBuilder/ImageLibrary.xml",
                 db_path="J:\\Mosaic\\database\\", tile_size=150):
        """
        Initialize Worker
        :param input_path: path to input image
        :param crop_size: crop size in px
        :param database: path to xml database file
        :param db_path: path to local image database
        :param tile_size: size per tile in output image in px
        """
        # initiate logging
        self.logger = logging.getLogger('Worker')
        handler = logging.FileHandler('./log.txt', 'a', 'UTF-8')
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s\t - %(process)s\t - %(name)s\t - %(funcName)s: %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)

        try:
            self.original_image = Image.open(input_path)
        except IOError as e:
            self.logger.critical("%s" % str(e))
            print(str(e))
            exit(-1)

        self.library = self.get_library(database)
        self.db_path = db_path
        self.crop_size = crop_size
        self.tile_size = tile_size
        self.tilesX, self.tilesY = self.get_tile_number()
        self.tiles_total = self.tilesX * self.tilesY
        self.logger.debug('%d/%d tiles, %d in total' % (self.tilesX, self.tilesY, self.tiles_total))

        # try to create output image
        try:
            self.result = Image.new('RGB', self.get_output_size())
        except MemoryError:
            self.logger.critical("Failed to create output image with %d/%d px. Memory error." % (self.get_output_size()))
            exit(-1)
        else:
            self.logger.info("Output image created with %d/%d px" % (self.get_output_size()))

    def get_imsize(self):
        """
        Get size of original image
        :return: tuple size of original image
        """
        return self.original_image.size

    def get_tile_number(self):
        """
        Get number of tiles in x and y perspective
        :return: tuple containing horizontal and vertical amount of tiles
        """
        w, h = self.get_imsize()
        return w // self.crop_size, h // self.crop_size

    def get_output_size(self):
        """
        Get size of output image as tuple
        :return: tuple containing size of resulting image
        """
        return self.tile_size * self.tilesX, self.tile_size * self.tilesY

    def get_tiles(self):
        """
        Extract tiles from original image and save in list
        :return: list of tiles
        """
        tiles = []
        for i in range(self.tilesY):
            for j in range(self.tilesX):
                box = (j * self.crop_size, i * self.crop_size, (j + 1) * self.crop_size, (i + 1) * self.crop_size)
                crop = self.original_image.crop(box)
                tile = Image.new('RGB', (self.crop_size, self.crop_size), 256)
                tile.paste(crop)
                tiles.append(tile)
        return tiles

    def get_colors_from_image(self, image, amount=1):
        """
        Get primary color(s) of an image
        :param image: an image
        :param amount:  number of colors to return
        :return: a map of colors in format #RRGGBB
        """
        # TODO: try different implementation of kmeans algorithm, e.g. from scikit
        colors = Cluster.colorz2(image, n=amount)
        return colors

    def get_quadrants(self, image):
        """
        Split an image into four quadrants
        :param image: an image
        :return: a list containing four images
        """
        imwidth, imheight = image.size
        width = imwidth // 2
        height = imheight // 2

        quad = []
        # split image. does not need to be exact, therefore simple algorithm used
        for i in range(imheight // height):
            for j in range(imwidth // width):
                box = (j * width, i * height, (j + 1) * width, (i + 1) * height)
                q = image.crop(box)
                quad.append(q)
        return quad

    def get_match(self, tile):
        """
        Determine best matching images in database for the specified input tile
        :param tile: an image
        :return: a dictionary of the best matches, sortable by difference to tile
        """
        diff = 1000
        matches = {}
        # split tile into quadrants and get dominant color of each one
        quads = self.get_quadrants(tile)
        orig_colors = []
        for quad in quads:
            orig_colors.append(list(self.get_colors_from_image(quad))[0])

        # loop through database entries and calculate euclidean difference between colors
        for artist in self.library.getchildren():
            for album in artist.getchildren():
                d = 0
                album_colors = (album.get('q0'), album.get('q1'),
                                album.get('q2'), album.get('q3'))

                for x, y in zip(orig_colors, album_colors):
                    d += self.difference(x, y)

                if d == 0:  # cannot reasonably happen, therefore an error must have occurred
                    continue
                elif d < diff:
                    diff = d
                    matches[d] = album.get('path')
        self.logger.debug("Found %d matches for tile." % len(matches))
        return matches

    def mosaic(self):
        """
        Create image mosaic from original in three steps:
        Collect tiles from original image, find best match for each tile, and combine them into a mosaic
        """
        self.logger.info('Mosaic creation started')
        match_dict = []
        tiles = self.get_tiles()

        print('worker (pid %d): started.' % os.getpid())
        for tile_no, tile in enumerate(tiles):
            # print status in 10%-steps
            if tile_no != self.tiles_total and (tile_no + 1) % (self.tiles_total // 10) == 0:
                print('worker (pid %d): %d percent done. (%d/%d)'
                      % (os.getpid(), ((tile_no + 1) / (self.tiles_total // 10)) * 10, tile_no + 1, self.tiles_total))

            matches = self.get_match(tile)
            match_found = False

            # loop through matches, starting with the best match (lowest difference)
            for key in sorted(matches):
                if key > MAX_DIFF:
                    # do not allow matches with difference > MAX_DIFF
                    break
                path = self.correct_path(matches[key])

                # avoid using the same tile twice right next to each other
                if len(matches) > 1:
                    if tile_no >= 1:
                        if match_dict[tile_no - 1] == path:
                            # if previous tile has same image, do not use match
                            continue
                    if tile_no >= self.tilesX:
                        if match_dict[tile_no - self.tilesX] == path:
                            # if tile one row above has same image, do not use match
                            continue

                # yay, best match found here
                match_found = True
                match_dict.append(path)
                self.logger.debug("%d/%d Match found at %s with a difference of %d"
                             % (tile_no + 1, self.tiles_total, path, key))
                break

            if not match_found:
                # if no 'perfect' match is found, still use the best available one (minimal difference)
                path = self.correct_path(matches[sorted(matches)[0]])
                match_dict.append(path)
                self.logger.debug("%d/%d Using duplicate match %s with a difference of %d"
                             % (tile_no + 1, self.tiles_total, path, sorted(matches)[0]))

        print('worker (pid %d): all matches found. assembling image from matches.' % os.getpid())
        # combine all matches into one image
        self.build_output(match_dict)
        print('worker (pid %d): finished.' % os.getpid())

    def build_output(self, tiles):
        """
        Build an image from list of tiles
        :param tiles: a list containing paths to tiles onw row after the other
        """
        self.logger.info('Assembling mosaic.')
        for i, tile_path in enumerate(tiles):
            tile = Image.open(tile_path)

            # convert output tile to desired size
            tile.thumbnail((self.tile_size, self.tile_size), Image.ANTIALIAS)

            x = i % self.tilesX
            y = i // self.tilesX
            box = (x * self.tile_size, y * self.tile_size, (x + 1) * self.tile_size, (y + 1) * self.tile_size)
            self.result.paste(tile, box)

    def difference(self, color1, color2):
        """
        Get euclidean difference of two hexadecimal color values
        :param color1: a string representing a hexadecimal color value
        :param color2: a string representing a hexadecimal color value
        :return: the euclidean difference of the two colors
        """
        r1, g1, b1 = self.hex2rgb(color1)
        r2, g2, b2 = self.hex2rgb(color2)
        return math.sqrt((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2)

    def hex2rgb(self, hex_color):
        """
        Return an R,G,B tuple from a hex color representation
        :param hex_color: a string representing a hexadecimal color value
        :return: an r,g,b tuple
        """
        # TODO:safety checks?
        value = hex_color.lstrip('#')
        length = len(value)
        return tuple(int(value[i:i + length // 3], 16) for i in range(0, length, length // 3))

    def correct_path(self, path):
        """
        Return a correct path to an image in the local database
        :param path: an image path (string)
        :return: the correct image path at self.db_path
        """
        # because image path is hardcoded in database, set to correct path in case the path differs
        if self.db_path not in path:
            new_path = os.path.join(self.db_path + path.split('\\')[-1])
            return new_path
        else:
            return path

    def get_library(self, lib_path):
        """
        Load library from xml file
        :param lib_path: path to library file
        :return: an etree tree
        """
        parser = etree.XMLParser(remove_blank_text=True, encoding="UTF-8")
        with open(lib_path, 'r') as f:
            try:
                library_tree = etree.parse(f, parser).getroot()
            except Exception as e:
                self.logger.critical('Could not parse database file: %s' % str(e))
                raise
        return library_tree


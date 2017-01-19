from Mosaic import Mosaic
import logging

# initiate logging
# logger = logging.getLogger(__name__)
# handler = logging.FileHandler('./log.txt', 'w', 'UTF-8')
# formatter = logging.Formatter('%(asctime)s - %(levelname)s\t - %(process)s\t - %(name)s\t - %(funcName)s: %(message)s')
# handler.setFormatter(formatter)
# logger.addHandler(handler)
# logger.setLevel(logging.DEBUG)


def main():
    Mosaic(input_path='./panda.jpg', database='../../photo_extractor/LibraryBuilder/ImageLibrary.xml',
           tile_divider=25, tile_size=20)

if __name__ == '__main__':
    # logger.info('Started.')
    main()
    # logger.info('Finished.')






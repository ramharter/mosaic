# mosaic
The MosaicBuilder application creates photo mosaics from a database of album covers.

The album covers must be available locally. 
To create a local database, run library.save_images_to_folder(path), where path is the desired location on your disc.
This might take a while.

If the local database is available, simply run Mosaic with parameters specifying source image and path to your local database.

e.g. Mosaic(input_path=path/to/your/image, db_path=path/to/your/database)

Enjoy!

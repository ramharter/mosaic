from library import *

"""
info: LibraryBuilder parses xml library file for artist names and assembles an album art library for those artists.
"""

path = "J:\\Mosaic\\database"
col = ArtistCollector()
artists = col.collect_artists()
lib = Library()

print('Number of artists in library:', lib.get_number_of_entries())
print('Number of album covers in library:', lib.get_number_of_albums())

# for artist in artists:
#     lib.add_artist(artist=artist)

# lib.get_latest_artists()
#
# lib.save_images_to_folder(path)
# lib.get_quad_colors()
# lib.write_etree()

print('Number of artists in library:', lib.get_number_of_entries())
print('Number of album covers in library:', lib.get_number_of_albums())

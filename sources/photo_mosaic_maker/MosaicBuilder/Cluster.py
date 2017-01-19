import logging
from collections import namedtuple
from math import sqrt
import random
from PIL import Image


Point = namedtuple('Point', ('coords', 'n', 'ct'))
Cluster = namedtuple('Cluster', ('points', 'center', 'n'))
rtoh = lambda rgb: '#%s' % ''.join(('%02x' % p for p in rgb))


def get_points(img):
    """
    Get list of color data points from image
    :param img: an image
    :return: points, a list
    """
    points = []
    w, h = img.size
    for count, color in img.getcolors(w * h):
        points.append(Point(color, 3, count))
    return points


def colorz(filename, n=3):
    """
    Get prominent colors from image file
    :param filename: path to image
    :param n: amount of colors to be found
    :return: a map of colors in hex notation
    """
    img = Image.open(filename)
    img.thumbnail((200, 200))

    points = get_points(img)
    clusters = kmeans(points, n, 1)
    rgbs = [map(int, c.center.coords) for c in clusters]
    return map(rtoh, rgbs)


def colorz2(img, n=3):
    """
    Get prominent colors from image
    :param img: an image
    :param n: amount of colors to be found
    :return: a map of colors in hex notation
    """
    img.thumbnail((200, 200))
    points = get_points(img)
    clusters = kmeans(points, n, 1)
    rgbs = [map(int, c.center.coords) for c in clusters]
    return map(rtoh, rgbs)


def euclidean(p1, p2):
    """ Get euclidean difference of two points """
    return sqrt(sum([
        (p1.coords[i] - p2.coords[i]) ** 2 for i in range(p1.n)
    ]))


def calculate_center(points, n):
    """
    Calculate center of cluster
    :param points: a list of points
    :param n:
    :return:
    """
    vals = [0.0 for i in range(n)]
    plen = 0
    for p in points:
        plen += p.ct
        for i in range(n):
            vals[i] += (p.coords[i] * p.ct)
    return Point([(v / plen) for v in vals], n, 1)


def kmeans(points, k, min_diff):
    """
    Get Cluster(s) from data
    :param points: a list of data points
    :param k: number of clusters to find
    :param min_diff: difference at which to stop
    :return: the found clusters
    """
    # look for k distinct colors, lower amount if necessary(j)
    for j in range(k, 0, -1):
        try:
            clusters = [Cluster([p], p, p.n) for p in random.sample(points, j)]
        except ValueError:
            logging.error("ValueError at i=%d" % j)
            continue
        else:
            break

    while 1:
        plists = [[] for i in range(j)]

        for p in points:
            # for each point:
            smallest_distance = float('Inf')
            for i in range(j):
                # go through each cluster and calculate difference between cluster center and point
                distance = euclidean(p, clusters[i].center)
                if distance < smallest_distance:
                    smallest_distance = distance
                    idx = i
            plists[idx].append(p)   # append point to the cluster with minimal difference

        diff = 0
        for i in range(j):
            #for each cluster
            old = clusters[i]
            # calculate new center (mean) of cluster
            center = calculate_center(plists[i], old.n)
            new = Cluster(plists[i], center, old.n)
            clusters[i] = new
            # calculate difference between old and new cluster mean
            diff = max(diff, euclidean(old.center, new.center))

        if diff < min_diff:
            # if minimal difference is reached, stop.
            break

    return clusters

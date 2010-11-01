import json
import os
import shutil
import urllib2


__author__ = 'Therms'
__tmdb_apikey__ = '6d96a9efb4752ed0d126d94e12e52036'

try:
    import imdb
    __imdb__ = True
except:
    __imdb__ = False

class XmgException(Exception):
    pass

class ApiError(XmgException):
    pass

class IdError(XmgException):
    pass

class NfoError(XmgException):
    pass

class metagen():
    def __init__(self, imdbid, imdbpy = None):
        ''' metagen is used to download metadata for a movie or tv show and then create
        the necessary files for the media to be imported into XBMC.

        Arguments
        ===========
        fanart/poster_height/width_min:  Sets lowest acceptable image resolution.  0 means
        disregard.  If no fanart available at specified resolution or greater, then
        we disregard this setting, and download highest resolution that is available.

        name*:  In the case of a movie, ideally this should be the full movie name
        followed by the year of the movie in parentheses. e.g. "The Matrix (1999)".
        If this is specific enough to generate only one search result then we'll
        continue. Otherwise, we'll raise IdError.

        Because of the imprecise nature of this method of id, only use it if you
        don't have the imdb_id or tmdb_id

        imdb_id:  Use this argument if you know the imdb id of the show/movie.  If
        this is used, the tmdb_id argument is ignored.

        tmdb_id*:  Use this argument if you know the tmdb id of the movie.  If this
        is used, the imdb_id argument is ignored.

        imdbpy:  When xmg is used as a library, imdbpy may not be installed
        system-wide, but included with your application.  If this is the case, pass
        your instance of imdb.IMDb() to metagen, so we can use it.

        *  These arguments are not yet supported.

        '''

        #first we'll evaluate our arguments for error conditions
        if not imdbpy and not __imdb__:
            raise ApiError("Can't import imdb and wasn't provided with an imdbpy instance")

        if imdbid[:2].lower() == 'tt':
            self.imdbid = imdbid[2:]

        if imdbpy:
            self.imdbpy = imdbpy
        else:
            self.imdbpy = imdb.IMDb()

        self.imdbpy_movie = self._get_movie()
        self.nfo_string = self._nfo_gen()
        self.tmdb_data = self._get_tmdb_imdb()

        #TODO: Search by movie name
        #TODO: Search by tmdb_id
        #TODO: Search by movie hash


    def _get_movie(self):
        try:
            imdbpy_movie = self.imdbpy.get_movie(self.imdbid)
        except imdb._exceptions.IMDbParserError:
            raise IdError("%s is not a valid imdb id" % self.imdbid)

        if len(imdbpy_movie.keys()) == 0:
            raise IdError("%s is not a valid imdb id" % self.imdbid)

        return imdbpy_movie

    def _nfo_gen(self):
        ''' Get the imdb url for the specified movie object
        '''
        nfo_string = self.imdbpy.get_imdbURL(self.imdbpy_movie)
        #TODO: Generate full nfo XML
        return nfo_string

    def write_nfo(self, path):
        try:
            f = open(path, 'w')
            f.write(self.nfo_string)
            f.close()
        except:
            raise NfoError("Couldn't write nfo")

    def _get_fanart(self, min_height, min_width):
        '''  Fetches the fanart for the specified imdb_id and saves it to dir.
        Arguments

        min_height/width: Sets lowest acceptable resolution fanart.  0 means
        disregard.  If no fanart available at specified resolution or greater, then
        we disregard.
        '''
        images = [image['image'] for image in self.tmdb_data['backdrops'] if image['image'].get('size') == 'original']
        if len(images) == 0:
            return

        return self._get_image(images, min_height, min_width)

    def get_fanart_url(self, min_height, min_width):
        return self._get_fanart(min_height, min_width)['url']

    def write_fanart(self, filename_root, path, min_height, min_width, orig_ext=True):
        fanart_url = self.get_fanart_url(min_height, min_width)
        #fetch and write to disk
        if orig_ext:
            dest = os.path.join(path, filename_root + os.path.splitext(fanart_url)[-1])
        else:
            dest = os.path.join(path, filename_root)
        try:
            f = open(dest, 'wb')
        except:
            raise IOError("Can't open for writing: %s" % dest)

        response = urllib2.urlopen(fanart_url)
        f.write(response.read())
        f.close()

        return True

    def _get_poster(self, min_height, min_width):
        '''  Fetches the poster for the specified imdb_id and saves it to dir.
        Arguments

        min_height/width: Sets lowest acceptable resolution poster.  0 means
        disregard.  If no poster available at specified resolution or greater, then
        we disregard.
        '''
        images = [image['image'] for image in self.tmdb_data['posters'] if image['image'].get('size') == 'original']
        if len(images) == 0:
            return

        return self._get_image(images, min_height, min_width)

    def get_poster_url(self, min_height, min_width):
        return self._get_poster(min_height, min_width)['url']

    def write_poster(self, filename_root, path, min_height, min_width, orig_ext=True):
        poster_url = self.get_poster_url(min_height, min_width)
        if orig_ext:
            dest = os.path.join(path, filename_root + os.path.splitext(poster_url)[-1])
        else:
            dest = os.path.join(path, filename_root)

        try:
            f = open(dest, 'wb')
        except:
            raise IOError("Can't open for writing: %s" % dest)

        response = urllib2.urlopen(poster_url)
        f.write(response.read())
        f.close()

        return True

    def _get_tmdb_imdb(self):
        url = "http://api.themoviedb.org/2.1/Movie.imdbLookup/en/json/%s/%s" % (__tmdb_apikey__, "tt" + self.imdbid)
        response = urllib2.urlopen(url)
        tmdb_data = json.loads(response.read())[0]
        return tmdb_data

    def _get_image(self, image_list, min_height, min_width):
        #Select image
        images = []
        for image in image_list:
            if not min_height or min_width:
                    images.append(image)
                    break
            elif min_height and not min_width:
                if image['height'] >= min_height:
                    images.append(image)
                    break
            elif min_width and not min_height:
                if image['width'] >= min_width:
                    images.append(image)
                    break
            elif min_width and min_height:
                if image['width'] >= min_width and image['height'] >= min_height:
                    images.append(image)
                    break

        #No image meets our resolution requirements, so disregard those requirements
        if len(images) == 0 and min_height or min_width:
            images.append(image_list[0])

        return images[0]


if __name__ == "__main__":
    import sys
    try:
        id = sys.argv[1]
    except:
        print "Type '%s _IMDBID_' to generate metadata." % sys.argv[0]
        sys.exit()

    x = metagen(id)
    x.write_nfo(".")
    x.write_fanart("fanart", ".", 0, 0)
    x.write_poster("movie", ".", 0, 0)

import json
import os
import urllib2
import re
from xml.etree.ElementTree import Element, SubElement, Comment, tostring
import xml.dom.minidom

__author__ = 'Therms'
__tmdb_apikey__ = '6d96a9efb4752ed0d126d94e12e52036'

class XmgException(Exception):
    pass

class ApiError(XmgException):
    pass

class IdError(XmgException):
    pass

class NfoError(XmgException):
    pass

class MetaGen():
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


        if imdbid[:2].lower() == 'tt':
            self.imdbid = imdbid[2:]
        else:
            self.imdbid = imdbid

        self.nfo_string = 'http://www.imdb.com/title/tt' + imdbid + '/'
        self.tmdb_data = self._get_tmdb_imdb()
        self._validate_tmdb_json()
        
        #TODO: Search by movie name
        #TODO: Search by tmdb_id
        #TODO: Search by movie hash
        
    
    def _validate_tmdb_json(self):
        try:
            _ = self._get_fanart(0,0)
        except:
            try:
                _ = self._get_poster(0,0)
            except:
                raise ApiError("Unknown TMDB data format: " % self.tmdb_data)
                
    def write_nfo(self, path, url = True, xml = True):

        self.out_string = ''

        if xml:
            self.out_string = self._generate_nfo_xml()

        if url:
            self.out_string = self.out_string + self.nfo_string
 
        try:
            f = open(path, 'w')
            f.write(self.out_string)
            f.close()
        except:
            raise NfoError("Couldn't write nfo")

    def _generate_nfo_xml(self):
        nfoxml = Element('movie')

        try:
            title = SubElement(nfoxml, 'title')
            title.text = self.tmdb_data['name']
        except:
            pass

        try:
            originaltitle = SubElement(nfoxml, 'originaltitel')
            originaltitle.text = self.tmdb_data['original_name']
        except:
            pass

        try:
            rating = SubElement(nfoxml, 'rating')
            rating.text = str(self.tmdb_data['rating'])
        except:
            pass

        try:
            year = SubElement(nfoxml, 'year')
            year.text = self.tmdb_data['released'][:4]
        except:
            pass

        try:
            votes = SubElement(nfoxml, 'votes')
            votes.text = str(self.tmdb_data['votes'])
        except:
            pass

        try:
            plot = SubElement(nfoxml, 'outline')
            plot.text = self.tmdb_data['overview']
        except:
            pass

        for genre in self.tmdb_data['genres']:
            genres = SubElement(nfoxml, 'genre')
            genres.text = genre['name']

        try:
            runtime = SubElement(nfoxml, 'runtime')
            runtime.text = str(self.tmdb_data['runtime']) + " min"
        except:
            pass

        try:
            premiered = SubElement(nfoxml, 'premiered')
            premiered.text = self.tmdb_data['released']
        except:
            pass

        try:
            mpaa = SubElement(nfoxml, 'mpaa')
            mpaa.text = self.tmdb_data['certification']
        except:
            pass

        try:
            id = SubElement(nfoxml, 'id')
            id.text = self.tmdb_data['imdb_id']
        except:
            pass

        # Clean up the xml and return it
        nfoxml = xml.dom.minidom.parseString(tostring(nfoxml))
        xml_string = nfoxml.toprettyxml(indent='  ')
        text_re = re.compile('>\n\s+([^<>\s].*?)\n\s+</', re.DOTALL)    
        xml_string = text_re.sub('>\g<1></', xml_string)

        return xml_string.encode('utf-8')

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

    def write_fanart(self, filename_root, path, min_height, min_width):
        fanart_url = self.get_fanart_url(min_height, min_width)
        #fetch and write to disk
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

    def write_poster(self, filename_root, path, min_height, min_width):
        poster_url = self.get_poster_url(min_height, min_width)
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
        
        count = 0
        while 1:
            count += 1
            response = urllib2.urlopen(url)
            json_string = response.read()
            try:
                tmdb_data = json.loads(json_string)[0]
                return tmdb_data
            except ValueError, e:
                if count < 3:
                    continue
                else:
                    raise ApiError("Invalid JSON: %s: %s" % e, json_string)
            except:
                ApiError("JSON error with: %s" % json_string)


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
        id = 'tt0111161'
    
    x = MetaGen(id)
    x.write_nfo(".\movie.nfo")
    x.write_fanart("fanart", ".", 0, 0)
    x.write_poster("movie", ".", 0, 0)

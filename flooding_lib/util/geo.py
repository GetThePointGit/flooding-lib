"""Helper functions for geo stuff."""

from pyproj import Proj, transform

import gdal

# Some projections

# Rijksdriehoeks stelsel.
RD = ("+proj=sterea +lat_0=52.15616055555555 +lon_0=5.38763888888889 "
      "+k=0.999908 +x_0=155000 +y_0=463000 +ellps=bessel "
      "+towgs84=565.237,50.0087,465.658,-0.406857,0.350733,-1.87035,4.0812 "
      "+units=m +no_defs")
GOOGLE = ('+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 '
          '+lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m '
          '+nadgrids=@null +no_defs +over')
RD_PROJECTION = Proj(RD)
GOOGLE_PROJECTION = Proj(GOOGLE)


class GeoImage(object):
    def __init__(self, filename):
        """Filename is a geo-aware image filename (e.g. a .png with
        accompanying .pgw). Its data is supposed to be in
        Rijksdriehoek projection."""
        self.filename = filename

    def extent(self):
        """Return extent of the image as a dict with keys minx, maxx,
        miny, maxy, in Google projection."""
        data = gdal.Open(self.filename)
        pixelsx = data.RasterXSize
        pixelsy = data.RasterYSize

        startx, dxx, dyx, starty, dxy, dyy = data.GetGeoTransform()

        endx = startx + (pixelsx - 1) * dxx
        endy = starty - (pixelsy - 1) * dyy

        startx, starty = transform(
            RD_PROJECTION, GOOGLE_PROJECTION, startx, starty)
        endx, endy = transform(
            RD_PROJECTION, GOOGLE_PROJECTION, endx, endy)

        if startx > endx:
            startx, endx = endx, startx
        if starty > endy:
            starty, endy = endy, starty

        return {
            'minx': startx,
            'maxx': endx,
            'miny': starty,
            'maxy': endy,
            }

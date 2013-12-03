# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""Models for the flooding_lib.tools.pyramids app. We store grids and
animations using gislib's pyramids, so that they can be served as WMS
by raster-server. These models keep track of what went where."""

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import gdal
import Image
import io
from matplotlib import cm
import numpy as np
import os

from django.conf import settings
from django.db import models
from django_extensions.db.fields import UUIDField
from django_extensions.db.fields.json import JSONField

from gislib import pyramids

SUBDIR_DEPTH = 6  # Number of characters of a UUID to use as directories


class Raster(models.Model):
    uuid = UUIDField(unique=True)

    def uuid_parts(self):
        chars = unicode(self.uuid)
        return (
            list(chars[:SUBDIR_DEPTH]) + [chars[SUBDIR_DEPTH:]])

    @property
    def pyramid_path(self):
        pyramid_base_dir = getattr(
            settings, 'PYRAMIDS_BASE_DIR',
            os.path.join(settings.BUILDOUT_DIR, 'var', 'pyramids'))

        return os.path.join(pyramid_base_dir, *self.uuid_parts())

    @property
    def pyramid(self):
        return pyramids.Pyramid(path=self.pyramid_path)

    @property
    def layer(self):
        return ':'.join(self.uuid_parts())

    def add(self, dataset, **kwargs):
        defaults = {
            'raster_size': (1024, 1024),
            'block_size': (256, 256)
            }
        defaults.update(kwargs)

        self.pyramid.add(dataset, **defaults)


class Animation(models.Model):
    """We don't store animations in pyramids anymore, but as
    individual geotiffs.  Filenames are of the form 'dataset0001.tiff'
    and they are stored in the results directory (same place as the
    old .pngs).

    This model keeps metadata of the animation. We _assume_ all frames
    are RD projection (28992)."""

    frames = models.IntegerField(default=0)
    cols = models.IntegerField(default=0)
    rows = models.IntegerField(default=0)
    geotransform = JSONField()
    basedir = models.TextField()

    def get_dataset_path(self, i):
        if not (0 <= i < self.frames):
            raise ValueError(
                "i must be a valid frame number, is {}, num frames is {}."
                .format(i, self.frames))

        return os.path.join(
            self.basedir.encode('utf8'), b'dataset{:04d}.tiff'.format(i))

    @property
    def bounds(self):
        x0, dxx, dxy, y0, dyx, dyy = self.geotransform['geotransform']

        # Note that JSONField returns Decimals, not floats...
        return {
            'west': float(x0),
            'east': float(x0 + self.cols * dxx),
            'north': float(y0),
            'south': float(y0 + self.rows * dyy),
            'projection': 28992,
        }

    @property
    def gridsize(self):
        # Assume square pixels, that is, dxx == dyy == gridsize
        return float(self.geotransform['geotransform'][1])  # dxx

    def __unicode__(self):
        return "{} frames in {}".format(self.frames, self.basedir)

    def save_image_to_response(self, response, framenr=0, colormap='PuBu'):
        dataset = gdal.Open(self.get_dataset_path(framenr))
        colormap = cm.get_cmap(colormap)

        # Get data as masked array
        data = np.ma.masked_equal(
            dataset.GetRasterBand(1).ReadAsArray(), 0, copy=False)

        # Apply colormap
        rgba = colormap(data, bytes=True)

        # Turn into PIL image
        image = Image.fromarray(rgba)

        # Save into response
        response['Content-type'] = 'image/png'
        image.save(response, 'png')

    def get_geotransform(self):
        return [float(g) for g in self.geotransform['geotransform']]

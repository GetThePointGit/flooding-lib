# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Animation.maxvalue'
        db.add_column('pyramids_animation', 'maxvalue', self.gf('django.db.models.fields.FloatField')(null=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Animation.maxvalue'
        db.delete_column('pyramids_animation', 'maxvalue')


    models = {
        'pyramids.animation': {
            'Meta': {'object_name': 'Animation'},
            'basedir': ('django.db.models.fields.TextField', [], {}),
            'cols': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'frames': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'geotransform': ('django.db.models.fields.TextField', [], {'default': "'{}'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'maxvalue': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'rows': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'pyramids.raster': {
            'Meta': {'object_name': 'Raster'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '36', 'blank': 'True'})
        }
    }

    complete_apps = ['pyramids']

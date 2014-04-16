# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'ShippingMethod'
        db.create_table(u'shipping_shippingmethod', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('code', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=128)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=128)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal(u'shipping', ['ShippingMethod'])

        # Adding M2M table for field countries on 'ShippingMethod'
        db.create_table(u'shipping_shippingmethod_countries', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('shippingmethod', models.ForeignKey(orm[u'shipping.shippingmethod'], null=False)),
            ('country', models.ForeignKey(orm[u'address.country'], null=False))
        ))
        db.create_unique(u'shipping_shippingmethod_countries', ['shippingmethod_id', 'country_id'])


    def backwards(self, orm):
        # Deleting model 'ShippingMethod'
        db.delete_table(u'shipping_shippingmethod')

        # Removing M2M table for field countries on 'ShippingMethod'
        db.delete_table('shipping_shippingmethod_countries')


    models = {
        u'address.country': {
            'Meta': {'ordering': "('-display_order', 'name')", 'object_name': 'Country'},
            'display_order': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0', 'db_index': 'True'}),
            'is_shipping_country': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'iso_3166_1_a2': ('django.db.models.fields.CharField', [], {'max_length': '2', 'primary_key': 'True'}),
            'iso_3166_1_a3': ('django.db.models.fields.CharField', [], {'max_length': '3', 'null': 'True', 'db_index': 'True'}),
            'iso_3166_1_numeric': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'db_index': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'printable_name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'shipping.orderanditemcharges': {
            'Meta': {'object_name': 'OrderAndItemCharges'},
            'code': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '128'}),
            'countries': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['address.Country']", 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'free_shipping_threshold': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '12', 'decimal_places': '2', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'}),
            'price_per_item': ('django.db.models.fields.DecimalField', [], {'default': "'0.00'", 'max_digits': '12', 'decimal_places': '2'}),
            'price_per_order': ('django.db.models.fields.DecimalField', [], {'default': "'0.00'", 'max_digits': '12', 'decimal_places': '2'})
        },
        u'shipping.shippingmethod': {
            'Meta': {'object_name': 'ShippingMethod'},
            'code': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '128'}),
            'countries': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['address.Country']", 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'})
        },
        u'shipping.weightband': {
            'Meta': {'ordering': "['upper_limit']", 'object_name': 'WeightBand'},
            'charge': ('django.db.models.fields.DecimalField', [], {'max_digits': '12', 'decimal_places': '2'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'method': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'bands'", 'to': u"orm['shipping.WeightBased']"}),
            'upper_limit': ('django.db.models.fields.FloatField', [], {})
        },
        u'shipping.weightbased': {
            'Meta': {'object_name': 'WeightBased'},
            'code': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '128'}),
            'countries': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['address.Country']", 'null': 'True', 'blank': 'True'}),
            'default_weight': ('django.db.models.fields.DecimalField', [], {'default': "'0.00'", 'max_digits': '12', 'decimal_places': '2'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'}),
            'upper_charge': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '12', 'decimal_places': '2'})
        }
    }

    complete_apps = ['shipping']
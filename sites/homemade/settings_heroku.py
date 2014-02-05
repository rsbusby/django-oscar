from settings import *
import os
#from memcacheify import memcacheify

PG_PASS = os.environ["PG_PASS"]
PG_NAME = os.environ["PG_NAME"]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': PG_NAME,
        'USER': 'scvfklsmfsskpz',
        'PASSWORD': PG_PASS,
        'HOST': 'ec2-54-225-123-71.compute-1.amazonaws.com',
        'PORT': '5432',
    }
}

TEMPLATE_DEBUG = False

TEMPLATE_LOADERS = (
    ('django.template.loaders.cached.Loader', (
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    )),
)

debugVal = os.environ['DEBUG']
if debugVal == 'True' or debugVal == '1':
    DEBUG=True
else:
    DEBUG=False

SITE_ID=2  ## set to 2 for www.homemade1616.com, 3 is heroku direct

## need to commit style files?? 
USE_LESS = False

COMPRESS_ENABLED = False
COMPRESS_PRECOMPILERS = (
    ('text/less', 'lessc {infile} {outfile}'),
)
COMPRESS_OFFLINE_CONTEXT = {
    'STATIC_URL': 'STATIC_URL',
    'use_less': USE_LESS,
}


COMPRESS_OFFLINE = True
COMPRESS_URL = STATIC_URL
COMPRESS_ROOT = STATIC_ROOT
COMPRESS_STORAGE = 'foodbucket.storage.CachedS3BotoStorage'
STATICFILES_STORAGE = 'foodbucket.storage.CachedS3BotoStorage'
AWS_LOCATION = ''
AWS_QUERYSTRING_EXPIRE = 7200
 

#CACHES = memcacheify()


CACHES = {
      'default': {
         'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
      }
  }

import mongoengine 

DB_NAME = os.environ['NEW_MONGO_DB']
DB_USERNAME = os.environ['NEW_MONGO_USERNAME'] 
DB_PASSWORD = os.environ['NEW_MONGO_PASS']
DB_HOST_ADDRESS = os.environ['NEW_MONGO_HOST_ADDRESS'] + DB_NAME

mongoengine.connect(DB_NAME, host='mongodb://' + DB_USERNAME + ':' + DB_PASSWORD + '@' + DB_HOST_ADDRESS)


USE_S3 = True

DEFAULT_FILE_STORAGE = 'storages.backends.s3boto.S3BotoStorage'
STATICFILES_STORAGE = 'storages.backends.s3boto.S3BotoStorage'


ALLOWED_HOSTS = ['www.homemade1616.com','homemade1616.com']

# the following should be enviroment variables
#AWS_ACCESS_KEY_ID = 'access-id'
#AWS_SECRET_ACCESS_KEY = 'secret-key'

AWS_STORAGE_BUCKET_NAME = 'foodbucket'
AWS_PRELOAD_METADATA = True # necessary to fix manage.py collectstatic command to only upload changed files instead of all files

AWS_QUERYSTRING_AUTH = False

MEDIA_ROOT=''



STATIC_URL = 'https://foodbucket.s3.amazonaws.com/'
MEDIA_URL = 'https://foodbucket.s3.amazonaws.com/uploads/'
FALSE_MEDIA_URL = STATIC_URL
ADMIN_MEDIA_PREFIX = 'https://bucket-name.s3.amazonaws.com/static/dj/admin/'


#GEOS_LIBRARY_PATH = '/app/.geodjango/geos/lib/libgeos_c.so'
#GDAL_LIBRARY_PATH = '/app/.geodjango/gdal/lib/libgdal.so'

# Haystack settings
HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.elasticsearch_backend.ElasticsearchSearchEngine',
        #'URL': os.environ['SEARCHBOX_URL'],
        'URL': os.environ['BONSAI_URL'],
        'INDEX_NAME': 'haystack',
        },
    }

HAYSTACK_SIGNAL_PROCESSOR = 'haystack.signals.RealtimeSignalProcessor'




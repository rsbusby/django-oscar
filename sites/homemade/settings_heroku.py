from settings import *
import os

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

DEBUG=True

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
 

import mongoengine 



DB_NAME = 'fooddb'
DB_USERNAME = 'heroku_app10788552'
DB_PASSWORD = os.environ['MONGO_PASS']
DB_HOST_ADDRESS = 'ds047437.mongolab.com:47437/' + DB_USERNAME

#print(DB_HOST_ADDRESS)

#connect(DB_NAME, host='mongodb://' + DB_USERNAME + ':' + DB_PASSWORD + '@' + DB_HOST_ADDRESS)

#MONGODB_DB = 'heroku_app10788552'#"my_food_db"

mongoengine.connect(DB_NAME, host='mongodb://' + DB_USERNAME + ':' + DB_PASSWORD + '@' + DB_HOST_ADDRESS)

MDB_SECRET_KEY="f00dut0pia"

USE_S3 = True

DEFAULT_FILE_STORAGE = 'storages.backends.s3boto.S3BotoStorage'
STATICFILES_STORAGE = 'storages.backends.s3boto.S3BotoStorage'

# the following should be enviroment variables
#AWS_ACCESS_KEY_ID = 'access-id'
#AWS_SECRET_ACCESS_KEY = 'secret-key'

AWS_STORAGE_BUCKET_NAME = 'foodbucket'
AWS_PRELOAD_METADATA = True # necessary to fix manage.py collectstatic command to only upload changed files instead of all files

AWS_QUERYSTRING_AUTH = False

MEDIA_ROOT=''



STATIC_URL = 'https://foodbucket.s3.amazonaws.com/static/'
MEDIA_URL = 'https://foodbucket.s3.amazonaws.com/static/uploads/'
FALSE_MEDIA_URL = STATIC_URL
ADMIN_MEDIA_PREFIX = 'https://bucket-name.s3.amazonaws.com/static/dj/admin/'

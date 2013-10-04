from settings import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'de9u8rsu0o47f0',
        'USER': 'scvfklsmfsskpz',
        'PASSWORD': 'ApwbzjaLG8OjskyWgA1qWeQTWY',
        'HOST': 'ec2-54-225-123-71.compute-1.amazonaws.com',
        'PORT': '5432',
    }
}


import mongoengine 


DB_NAME = 'foodb'
DB_USERNAME = 'heroku_app10788552'
DB_PASSWORD = 'sdjmq74cqnas81j3jgtttcvvp0'
DB_HOST_ADDRESS = 'ds047437.mongolab.com:47437/' + DB_USERNAME

#print(DB_HOST_ADDRESS)

#connect(DB_NAME, host='mongodb://' + DB_USERNAME + ':' + DB_PASSWORD + '@' + DB_HOST_ADDRESS)

#MONGODB_DB = 'heroku_app10788552'#"my_food_db"

mongoengine.connect(DB_NAME, host='mongodb://' + DB_USERNAME + ':' + DB_PASSWORD + '@' + DB_HOST_ADDRESS)

MDB_SECRET_KEY="f00dut0pia"
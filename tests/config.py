import os
import django

from django.conf import settings, global_settings
from oscar import OSCAR_CORE_APPS, OSCAR_MAIN_TEMPLATE_DIR


def configure():

    print "configure settings"

    if not settings.configured:
        #from oscar.defaults import OSCAR_SETTINGS
        from oscar.defaults import OSCAR_SETTINGS

        # Helper function to extract absolute path
        location = lambda x: os.path.join(
            os.path.dirname(os.path.realpath(__file__)), x)

        import sys
        sys.path.append("./sites/homemade")
        sys.path.append("./apps/homemade")


        test_settings = {
            'DATABASES': {
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': ':memory:',
                },
            },
            'MONGO_TEST': True,
            'USE_S3':False,
            'INSTALLED_APPS': [
                'django.contrib.auth',
                'django.contrib.admin',
                'django.contrib.contenttypes',
                'django.contrib.sessions',
                'django.contrib.sites',
                'django.contrib.flatpages',
                'django.contrib.staticfiles',
                'sorl.thumbnail',
                'crispy_forms',
                'compressor',
                'apps.homemade',
            ] + OSCAR_CORE_APPS,
            'TEMPLATE_CONTEXT_PROCESSORS': (
                "django.contrib.auth.context_processors.auth",
                "django.core.context_processors.request",
                "django.core.context_processors.debug",
                "django.core.context_processors.i18n",
                "django.core.context_processors.media",
                "django.core.context_processors.static",
                "django.contrib.messages.context_processors.messages",
                'oscar.apps.search.context_processors.search_form',
                'oscar.apps.customer.notifications.context_processors.notifications',
                'oscar.apps.promotions.context_processors.promotions',
                'oscar.apps.checkout.context_processors.checkout',
            ),
            'TEMPLATE_DIRS': (
                location('templates'),
                OSCAR_MAIN_TEMPLATE_DIR,
            ),
            'MIDDLEWARE_CLASSES': global_settings.MIDDLEWARE_CLASSES + (
                'oscar.apps.basket.middleware.BasketMiddleware',
            ),
            'AUTHENTICATION_BACKENDS': (
                'oscar.apps.customer.auth_backends.Emailbackend',
                'django.contrib.auth.backends.ModelBackend',
            ),
            'HAYSTACK_CONNECTIONS': {
                'default': {
                    'ENGINE': 'haystack.backends.simple_backend.SimpleEngine',
                }
            },
            'PASSWORD_HASHERS': ['django.contrib.auth.hashers.MD5PasswordHasher'],
            ##'ROOT_URLCONF': 'tests._site.urls',
            'ROOT_URLCONF': 'urls',

            'LOGIN_REDIRECT_URL': '/accounts/',
            'STATIC_URL': '/static/',
            'COMPRESS_ENABLED': False,
            'ADMINS': ('admin@example.com',),
            'DEBUG': False,
            'PAY_IN_PERSON': True,
            'SITE_ID': 1,
            'APPEND_SLASH': True,
            'MONGODB_DB' :'my_test_db',
            'MDB_SECRET_KEY':"f00dut0pia",
            'EASYPOST_KEY':os.environ['EASYPOST_KEY_TEST'],
            # Currency
            'OSCAR_DEFAULT_CURRENCY':'USD',

            'OSCAR_CURRENCY_LOCALE':'en_US',
            'TEST_LOCAL':True,
            'CHECKOUT_ENABLED':True,



        }
        #if django.VERSION >= (1, 5):
        #    #test_settings['INSTALLED_APPS'] += ['tests._site.myauth', ]
        #    #test_settings['AUTH_USER_MODEL'] = 'myauth.User'
        #    test_settings['AUTH_USER_MODEL'] = 'auth.User'            

        test_settings.update(OSCAR_SETTINGS)
    

        import mongoengine 

        settings.configure(**test_settings)
        #settings.MONGODB_DB = "test_db"

        mongoengine.connect(settings.MONGODB_DB) 
        print "YEAH setting Mongo DB in test config,  " + settings.MONGODB_DB



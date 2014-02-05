import os

##FORCE_SCRIPT_NAME="/oscar"


# Path helper
PROJECT_DIR = os.path.dirname(__file__)
location = lambda x: os.path.join(
    os.path.dirname(os.path.realpath(__file__)), x)

USE_TZ = True

DEBUG = True
TEMPLATE_DEBUG = False
SQL_DEBUG = True
SEND_BROKEN_LINK_EMAILS = False

ADMINS = (
    ('Richard Busby', 'rsbusby@gmail.com'),
)

MANAGERS = ADMINS



DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'oscarhome',
        'USER': 'doscar',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}


# Use a Sqlite database by default
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': os.path.join(os.path.dirname(__file__), 'db.sqlite'),
#         'USER': '',
#         'PASSWORD': '',
#         'HOST': '',
#         'PORT': '',
#     }
# }

CACHES = {
    'default': {
        'BACKEND':
        'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
    }
}



INSTALLED_APPS =[]


#TEMPLATE_LOADERS = (
#    'jinja2_for_django.Loader',
#)

#TEMPLATE_LOADERS = (
#    'django_jinja.loaders.AppLoader',
#    'django_jinja.loaders.FileSystemLoader',
#)

# More advanced method. Intercept all templates
# except from django admin.
#DEFAULT_JINJA2_TEMPLATE_INTERCEPT_RE = r"^(?!admin/).*"

INSTALLED_APPS += ('django_jinja',)
#DEFAULT_JINJA2_TEMPLATE_EXTENSION = '.jinja.html'

# Same behavior of default intercept method
# by extension but using regex (not recommended)
DEFAULT_JINJA2_TEMPLATE_INTERCEPT_RE = r'.*jinja$'


# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Los_Angeles'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

# This should match the locale folders in oscar/locale
LANGUAGES = (
 #   ('en-gb', 'English'),
 #   ('da', 'Danish'),
 #   ('de', 'German'),
 #   ('el', 'Greek'),
    ('en', 'English'),
 #   ('es', 'Spanish'),
 #   ('fr', 'French'),
 #   ('it', 'Italian'),
 #   ('ja', 'Japanese'),
 #   ('pl', 'Polish'),
 #   ('pt', 'Portugese'),
 #   ('ru', 'Russian'),
 #   ('sk', 'Slovakian'),
)
ROSETTA_STORAGE_CLASS = 'rosetta.storage.SessionRosettaStorage'
ROSETTA_ENABLE_TRANSLATION_SUGGESTIONS = True
ROSETTA_REQUIRES_AUTH = False

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = location("public/media")

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
#ADMIN_MEDIA_PREFIX = '/media/admin/'

STATIC_URL = '/static/'

STATIC_ROOT = location('public/static')
STATICFILES_DIRS = (
    location('static/'),   location('../../oscar/static/oscar')
        )
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '$)a7n&o80u!6y5t-+jrd3)3!%vh&shg$wqpjpxc!ar&p#!)n1a'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
 ##   'django_jinja.loaders.AppLoader',
 ##   'django_jinja.loaders.FileSystemLoader',
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    # needed by django-treebeard for admin (and potentially other libs)
    #'django.template.loaders.eggs.Loader',
 
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.request",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.contrib.messages.context_processors.messages",
    # Oscar specific
    'oscar.apps.search.context_processors.search_form',
    'oscar.apps.promotions.context_processors.promotions',
    'oscar.apps.checkout.context_processors.checkout',
    'oscar.core.context_processors.metadata',
    'oscar.apps.customer.notifications.context_processors.notifications',
    # mine
    
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    ##'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.RemoteUserMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.transaction.TransactionMiddleware',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
    #'debug_toolbar.middleware.DebugToolbarMiddleware',
    # Allow languages to be selected
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    # Ensure a valid basket is added to the request instance for every request
    'oscar.apps.basket.middleware.BasketMiddleware',
    # Enable the ProfileMiddleware, then add ?cprofile to any
    # URL path to print out profile details
    'oscar.profiling.middleware.ProfileMiddleware',
)


ROOT_URLCONF = 'urls'

# Add another path to Oscar's templates.  This allows templates to be
# customised easily.

from oscar import OSCAR_MAIN_TEMPLATE_DIR
TEMPLATE_DIRS = (
    location('templates'),
    OSCAR_MAIN_TEMPLATE_DIR,
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(message)s',
        },
        'simple': {
            'format': '[%(asctime)s] %(message)s'
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'null': {
            'level': 'DEBUG',
            'class': 'django.utils.log.NullHandler',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'checkout_file': {
            'level': 'INFO',
            'class': 'oscar.core.logging.handlers.EnvFileHandler',
            'filename': 'checkout.log',
            'formatter': 'verbose'
        },
        'gateway_file': {
            'level': 'INFO',
            'class': 'oscar.core.logging.handlers.EnvFileHandler',
            'filename': 'gateway.log',
            'formatter': 'simple'
        },
        'error_file': {
            'level': 'INFO',
            'class': 'oscar.core.logging.handlers.EnvFileHandler',
            'filename': 'errors.log',
            'formatter': 'verbose'
        },
        'sorl_file': {
            'level': 'INFO',
            'class': 'oscar.core.logging.handlers.EnvFileHandler',
            'filename': 'sorl.log',
            'formatter': 'verbose'
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'filters': ['require_debug_false'],
        },
    },
    'loggers': {
        'django': {
            'handlers': ['null'],
            'propagate': True,
            'level': 'INFO',
        },
        'django.request': {
            'handlers': ['mail_admins', 'error_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'oscar.checkout': {
            'handlers': ['console', 'checkout_file'],
            'propagate': True,
            'level': 'INFO',
        },
        'oscar.catalogue.import': {
            'handlers': ['console'],
            'propagate': False,
            'level': 'INFO',
        },
        'gateway': {
            'handlers': ['gateway_file'],
            'propagate': True,
            'level': 'INFO',
        },
        'sorl.thumbnail': {
            'handlers': ['sorl_file'],
            'propagate': True,
            'level': 'INFO',
        },
        'django.db.backends': {
            'handlers': ['null'],
            'propagate': False,
            'level': 'DEBUG',
        },
        # suppress output of this debug toolbar panel
        'template_timings_panel': {
            'handlers': ['null'],
            'level': 'DEBUG',
            'propagate': False,
        }
    }
}


INSTALLED_APPS = INSTALLED_APPS + [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.admin',
    'django.contrib.flatpages',
    'django.contrib.staticfiles',
    'django_extensions',
    # Debug toolbar + extensions
    #'debug_toolbar',
    'djrill',
    'haystack',
    'crispy_forms',
    #'cache_panel',
    #'template_timings_panel',
    'storages',
    'south',
    'rosetta',          # For i18n testing
    #'compressor',
    #'apps.user',        # For profile testing
    'apps.homemade',        # include models from local app
    #'apps.gateway',     # For allowing dashboard access
    ##'endless_pagination',
]
from oscar import get_core_apps
INSTALLED_APPS = INSTALLED_APPS + get_core_apps()

# Add Oscar's custom auth backend so users can sign in using their email
# address.
AUTHENTICATION_BACKENDS = (
    'oscar.apps.customer.auth_backends.Emailbackend',
    'django.contrib.auth.backends.ModelBackend',
    'django.contrib.auth.backends.RemoteUserBackend',
)

LOGIN_URL = '/'
LOGIN_REDIRECT_URL = '/catalogue/'
APPEND_SLASH = True

# Haystack settings
HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
        'PATH': os.path.join(os.path.dirname(__file__), 'whoosh_index'),
    },
}

# =============
# Debug Toolbar
# =============

#INTERNAL_IPS = ('127.0.0.1',)

def show_toolbar(request):
    return request.user.is_staff


# Allow internal IP's to see the debug toolbar.  
def is_internal(request):
    ip_addr = request.META['REMOTE_ADDR']
    return ip_addr in INTERNAL_IPS or ip_addr.startswith('192.168')

DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False,
    'SHOW_TOOLBAR_CALLBACK': show_toolbar,
}
DEBUG_TOOLBAR_PANELS = (
    'debug_toolbar.panels.headers.HeaderDebugPanel',
    'debug_toolbar.panels.request_vars.RequestVarsDebugPanel',
    'debug_toolbar.panels.template.TemplateDebugPanel',
    'debug_toolbar.panels.timer.TimerDebugPanel',
    'debug_toolbar.panels.sql.SQLDebugPanel',
    #'template_timings_panel.panels.TemplateTimings.TemplateTimings',
    #'cache_panel.panel.CacheDebugPanel',
    'debug_toolbar.panels.signals.SignalDebugPanel',
    'debug_toolbar.panels.logger.LoggingPanel',
    'debug_toolbar.panels.version.VersionDebugPanel',
    'debug_toolbar.panels.settings_vars.SettingsVarsDebugPanel',
)

# ==============
# Oscar settings
# ==============

from oscar.defaults import *


SITE_ID=2

## testing 
SOUTH_TESTS_MIGRATE = False

## from hacky import from HOMEMADE code
IMPORTING=False

## email/Mandrill setup
OSCAR_FROM_EMAIL = "Homemade 1616 <support@homemade1616.com>"
print OSCAR_FROM_EMAIL
MANDRILL_API_KEY = os.environ['MANDRILL_API_KEY']


## shipping setup
POSTMASTER_IO_KEY = os.environ['POSTMASTER_IO_KEY_TEST']
EASYPOST_KEY = os.environ['EASYPOST_KEY']

EMAIL_SUBJECT_PREFIX = ''
##EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_BACKEND = "djrill.mail.backends.djrill.DjrillBackend"


## MINE
##AUTH_USER_MODEL = 'user.ExtenderUserModel'
#AUTH_USER_MODEL = 'customer.AbstractUser'
OSCAR_EAGER_ALERTS=True
OSCAR_DEFAULT_CURRENCY='USD'
OSCAR_CURRENCY_LOCALE = 'en_US'
# Address settings
OSCAR_REQUIRED_ADDRESS_FIELDS = ('first_name', 'last_name', 'line1',
                                 'line4', 'postcode' )
TEST_LOCAL=False
CHECKOUT_ENABLED=os.environ['CHECKOUT_ENABLED']
PAY_IN_PERSON=os.environ['PAY_IN_PERSON']

CRISPY_TEMPLATE_PACK = 'bootstrap'


# Reviews
OSCAR_ALLOW_ANON_REVIEWS = False
OSCAR_MODERATE_REVIEWS = True

# Meta
# ====

OSCAR_SHOP_NAME = 'HomeMade 1616'
OSCAR_SHOP_TAGLINE = ''

# Enter Google Analytics ID for the tracking to be included in the templates
GOOGLE_ANALYTICS_ID = os.environ['GOOGLE_ANALYTICS_ID']
GOOGLE_MAPS_KEY = os.environ['GOOGLE_MAPS_KEY']

OSCAR_RECENTLY_VIEWED_PRODUCTS = 21
OSCAR_ALLOW_ANON_CHECKOUT = False


OSCAR_PRODUCTS_PER_PAGE = 21

# This is added to each template context by the core context processor.  It is
# useful for test/stage/qa sites where you want to show the version of the site
# in the page title.
DISPLAY_VERSION = False


# Order processing
# ================

# Some sample order/line status settings
OSCAR_INITIAL_ORDER_STATUS = 'Pending'
OSCAR_INITIAL_LINE_STATUS = 'Pending'
OSCAR_ORDER_STATUS_PIPELINE = {
    'Pending': ('Being processed', 'Cancelled',),
    'Being processed': ('Processed', 'Cancelled',),
    'Cancelled': (),
}


# LESS/CSS/statics
# ================

# We default to using CSS files, rather than the LESS files that generate them.
# If you want to develop Oscar's CSS, then set USE_LESS=True and
# COMPRESS_ENABLED=False in your settings_local module and ensure you have
# 'lessc' installed.  You can do this by running:
#
#    pip install -r requirements_less.txt
#
# which will install node.js and less in your virtualenv.

USE_LESS = False

COMPRESS_ENABLED = False
COMPRESS_PRECOMPILERS = (
    ('text/less', 'lessc {infile} {outfile}'),
)
COMPRESS_OFFLINE_CONTEXT = {
    'STATIC_URL': 'STATIC_URL',
    'use_less': USE_LESS,
}

# We do this to work around an issue in compressor where the LESS files are
# compiled but compression isn't enabled.  When this happens, the relative URL
# is wrong between the generated CSS file and other assets:
# https://github.com/jezdez/django_compressor/issues/226
COMPRESS_OUTPUT_DIR = 'oscar'

# Logging
# =======

LOG_ROOT = location('logs')
# Ensure log root exists
if not os.path.exists(LOG_ROOT):
    os.mkdir(LOG_ROOT)

# Sorl
# ====

THUMBNAIL_DEBUG = True
THUMBNAIL_KEY_PREFIX = 'oscar-sandbox'


# Search facets
from django.utils.translation import ugettext_lazy as _

OSCAR_SEARCH_FACETS = {
    'fields': {},
    # 'fields': {
    #     # The key for these dicts will be used when passing facet data
    #     # to the template. Same for the 'queries' dict below.
    #     'category': {
    #         'name': _('Category'),
    #         'field': 'category'
    #     }
    # },
    'queries': {
        'price_range': {
            'name': _('Price range'),
            'field': 'price',
            'queries': [
                # This is a list of (name, query) tuples where the name will
                # be displayed on the front-end.
                (_('0 to 2.25'), '[0 TO 2.25]'),
                (_('2.25 to 4'), '[2.25 TO 4]'),
                (_('4 to 6'), '[4 TO 6]'),
                (_('6+'), '[6 TO *]'),
            ]
        }
    }
}


# Try and import local settings which can be used to override any of the above.
try:
    from settings_local import *
except ImportError:
    pass

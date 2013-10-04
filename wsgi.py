
import os
import sys

# Project root
root = 'sites/homemade'
sys.path.insert(0, root)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings_heroku")

# This application object is used by the development server
# as well as any WSGI server configured to use this file.
from django.core.wsgi import get_wsgi_application


from dj_static import Cling

application = Cling(get_wsgi_application())

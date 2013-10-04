#!/usr/bin/env python
import os
import sys

import settings_postgres as settings # Assumed to be in the same directory.

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

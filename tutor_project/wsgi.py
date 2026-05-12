import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tutor_project.settings")

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()

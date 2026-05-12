import os
import sys
from pathlib import Path

import django
from dotenv import load_dotenv

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
load_dotenv(root / '.env', override=True)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tutor_project.settings")
django.setup()

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()

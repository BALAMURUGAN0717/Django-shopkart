import os
import sys
from pathlib import Path

# Add joes_project to sys.path so Django can locate joes_project/settings.py and apps
base_dir = Path(__file__).resolve().parent / 'joes_project'
sys.path.insert(0, str(base_dir))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'joes_project.settings')

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
app = application

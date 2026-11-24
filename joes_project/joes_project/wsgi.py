import os
import sys
from pathlib import Path

# Ensure paths are on sys.path
base_dir = Path(__file__).resolve().parent.parent
if str(base_dir) not in sys.path:
    sys.path.insert(0, str(base_dir))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'joes_project.settings')

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
app = application

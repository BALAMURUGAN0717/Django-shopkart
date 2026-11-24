import os
import sys
import urllib.parse
from pathlib import Path

# Add joes_project to sys.path so Django can locate joes_project/settings.py and apps
base_dir = Path(__file__).resolve().parent / 'joes_project'
if str(base_dir) not in sys.path:
    sys.path.insert(0, str(base_dir))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'joes_project.settings')

from django.core.wsgi import get_wsgi_application

_django_app = get_wsgi_application()


def application(environ, start_response):
    # Ensure PATH_INFO is unquoted according to PEP 3333 in serverless runtimes
    if 'PATH_INFO' in environ and '%' in environ['PATH_INFO']:
        try:
            environ['PATH_INFO'] = urllib.parse.unquote(environ['PATH_INFO'])
        except Exception:
            pass
    return _django_app(environ, start_response)


app = application

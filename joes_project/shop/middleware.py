"""
Middleware for seamless session synchronization, URL unquoting, and cache control
in serverless deployment environments (e.g., Vercel, AWS Lambda).
"""
import urllib.parse
from django.contrib.auth.models import User


class ServerlessSessionSyncMiddleware:
    """
    1. Unquotes request.path_info to guarantee PEP 3333 compliance across serverless bridges.
    2. Synchronizes user accounts from signed session cookies across ephemeral instances.
    3. Auto-seeds initial catalog if database is empty.
    4. Enforces Cache-Control headers on HTML responses so Edge CDN never caches authenticated pages.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self._seeded = False

    def __call__(self, request):
        # 1. Ensure path_info is cleanly unquoted for URL routing
        if hasattr(request, 'path_info') and '%' in request.path_info:
            try:
                request.path_info = urllib.parse.unquote(request.path_info)
            except Exception:
                pass

        # 2. Sync user before AuthenticationMiddleware loads request.user
        if hasattr(request, 'session'):
            meta = request.session.get('_auth_user_meta')
            if meta and isinstance(meta, dict):
                uid = meta.get('id')
                uname = meta.get('username')
                if uid and uname:
                    try:
                        if not User.objects.filter(pk=uid).exists() and not User.objects.filter(username=uname).exists():
                            user = User(
                                id=uid,
                                username=uname,
                                email=meta.get('email', ''),
                                password=meta.get('password', ''),
                                is_active=meta.get('is_active', True),
                                is_staff=meta.get('is_staff', False),
                                is_superuser=meta.get('is_superuser', False),
                            )
                            user.save()
                    except Exception:
                        pass

        # 3. Auto-seed catalog if database is empty (e.g. freshly deployed instance or external DB)
        if not self._seeded:
            try:
                from shop.models import Catagory
                if Catagory.objects.count() == 0:
                    from django.core.management import call_command
                    call_command('loaddata', 'initial_data.json', verbosity=0)
                self._seeded = True
            except Exception:
                self._seeded = True

        response = self.get_response(request)

        # 4. Prevent edge CDN caching on all HTML views
        content_type = response.get('Content-Type', '')
        if 'text/html' in content_type:
            response['Cache-Control'] = 'private, no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'

        return response

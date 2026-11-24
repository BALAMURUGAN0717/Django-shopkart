"""
Middleware for seamless session synchronization and cache control
in serverless deployment environments (e.g., Vercel, AWS Lambda).
"""
from django.contrib.auth.models import User


class ServerlessSessionSyncMiddleware:
    """
    1. Synchronizes user accounts from signed session cookies across
       ephemeral serverless instances when using SQLite fallback.
    2. Enforces Cache-Control headers on HTML responses so Vercel Edge
       CDN never caches authenticated dynamic pages.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Sync user before AuthenticationMiddleware loads request.user
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

        response = self.get_response(request)

        # 2. Prevent edge CDN caching on all HTML views
        content_type = response.get('Content-Type', '')
        if 'text/html' in content_type:
            response['Cache-Control'] = 'private, no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'

        return response

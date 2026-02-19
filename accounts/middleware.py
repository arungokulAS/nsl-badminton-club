from django.shortcuts import redirect

class AdminRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        admin_paths = [
            '/admin/teams', '/admin/groups', '/admin/schedule', '/admin/live-manage', '/admin/finish-round', '/admin/dashboard'
        ]
        if any(request.path.startswith(p) for p in admin_paths):
            if not request.session.get('is_admin'):
                return redirect('/admin/login')
        return self.get_response(request)

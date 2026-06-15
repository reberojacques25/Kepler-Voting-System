from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from functools import wraps

def staff_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, "Admin access required.")
            return redirect("dashboard:student")
        return view_func(request, *args, **kwargs)
    return _wrapped

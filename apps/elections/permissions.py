from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from functools import wraps

def verified_and_allowed_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        user = request.user
        if not getattr(user, "is_email_verified", False):
            messages.error(request, "Please verify your email before accessing elections.")
            return redirect("dashboard:student")
        if not getattr(user, "can_vote", True):
            messages.error(request, "Your voting access has been blocked. Please contact the election administrator.")
            return redirect("dashboard:student")
        return view_func(request, *args, **kwargs)
    return _wrapped

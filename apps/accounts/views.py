from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.signing import BadSignature, SignatureExpired

from .forms import StudentSignUpForm, EmailOrStudentIDAuthenticationForm
from .utils import send_verification_email, parse_email_token

User = get_user_model()

def signup(request):
    if request.user.is_authenticated:
        return redirect("dashboard:student")

    if request.method == "POST":
        form = StudentSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            send_verification_email(user)
            messages.success(request, "Account created! Please check your email to verify and activate your account.")
            return render(request, "accounts/verify_sent.html", {"email": user.email})
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = StudentSignUpForm()

    return render(request, "accounts/signup.html", {"form": form})

class StudentLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = EmailOrStudentIDAuthenticationForm

    def form_valid(self, form):
        user = form.get_user()
        if not user.is_active or not getattr(user, "is_email_verified", False):
            messages.error(self.request, "Your account is not verified yet. Please check your email for the verification link.")
            return redirect("accounts:login")
        return super().form_valid(form)

def verify_email(request, token):
    try:
        user_id = parse_email_token(token)
        user = User.objects.get(id=user_id)
        user.is_active = True
        user.is_email_verified = True
        user.save(update_fields=["is_active", "is_email_verified"])
        messages.success(request, "Email verified successfully. You can now log in.")
        return render(request, "accounts/verify_result.html", {"status": "success"})
    except (BadSignature, SignatureExpired, User.DoesNotExist):
        messages.error(request, "Verification link is invalid or expired. Please request a new verification email.")
        return render(request, "accounts/verify_result.html", {"status": "failed"})

@login_required
def resend_verification(request):
    if request.user.is_email_verified:
        messages.info(request, "Your email is already verified.")
        return redirect("dashboard:student")
    send_verification_email(request.user)
    messages.success(request, "Verification email sent. Please check your inbox.")
    return redirect("dashboard:student")

@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "Logged out successfully.")
    return redirect("core:home")

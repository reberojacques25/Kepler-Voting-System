from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("elections/", include("apps.elections.urls")),
    path("dashboard/", include("apps.dashboard.urls")),
    path('history/', include('apps.history.urls')),
    path('accounts/password-reset/',
     auth_views.PasswordResetView.as_view(
         template_name='accounts/password_reset.html',
         email_template_name='accounts/password_reset_email.html',
         subject_template_name='accounts/password_reset_subject.txt',
         success_url='/accounts/password-reset/done/',
     ),
     name='password_reset'),
path('accounts/password-reset/done/',
     auth_views.PasswordResetDoneView.as_view(
         template_name='accounts/password_reset_done.html',
     ),
     name='password_reset_done'),
path('accounts/password-reset/confirm/<uidb64>/<token>/',
     auth_views.PasswordResetConfirmView.as_view(
         template_name='accounts/password_reset_confirm.html',
         success_url='/accounts/password-reset/complete/',
     ),
     name='password_reset_confirm'),
path('accounts/password-reset/complete/',
     auth_views.PasswordResetCompleteView.as_view(
         template_name='accounts/password_reset_complete.html',
     ),
     name='password_reset_complete'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

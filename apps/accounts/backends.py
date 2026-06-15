from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()

class EmailOrStudentIDBackend(ModelBackend):
    """Authenticate using email OR student_id in the 'username' field."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        key = username.strip()
        if not key:
            return None

        try:
            user = User.objects.get(Q(email__iexact=key) | Q(student_id__iexact=key) | Q(username__iexact=key))
        except User.DoesNotExist:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

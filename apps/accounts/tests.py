from django.core import mail
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.accounts.utils import make_email_token
from apps.elections.tests.factories import PASSWORD, make_student


class SignUpAndVerificationTests(TestCase):
    def signup(self, **overrides):
        data = {
            "email": "New.Student@Kepler.ac.rw",
            "student_id": "kpl-777",
            "password1": PASSWORD,
            "password2": PASSWORD,
        }
        data.update(overrides)
        return self.client.post(reverse("accounts:signup"), data)

    def test_signup_creates_inactive_account_and_sends_email(self):
        self.signup()
        user = User.objects.get()
        self.assertEqual(user.email, "new.student@kepler.ac.rw")
        self.assertEqual(user.student_id, "KPL-777")
        self.assertFalse(user.is_active)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/accounts/verify/", mail.outbox[0].body)

    def test_duplicate_email_or_student_id_rejected(self):
        make_student(email="taken@kepler.ac.rw", student_id="KPL-777")
        self.signup(email="TAKEN@kepler.ac.rw", student_id="KPL-888")
        self.signup(email="free@kepler.ac.rw", student_id="kpl-777")
        self.assertEqual(User.objects.count(), 1)

    def test_verification_link_activates_account(self):
        self.signup()
        user = User.objects.get()
        self.client.get(reverse("accounts:verify_email", args=[make_email_token(user.id)]))
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_email_verified)

    def test_tampered_token_rejected(self):
        self.signup()
        user = User.objects.get()
        self.client.get(reverse("accounts:verify_email", args=[make_email_token(user.id) + "x"]))
        user.refresh_from_db()
        self.assertFalse(user.is_active)


class LoginTests(TestCase):
    def login(self, username):
        return self.client.post(reverse("accounts:login"), {"username": username, "password": PASSWORD})

    def test_login_with_email_or_student_id(self):
        make_student(email="a@kepler.ac.rw", student_id="KPL-1")
        for username in ["a@kepler.ac.rw", "kpl-1"]:
            with self.subTest(username=username):
                self.client.logout()
                self.login(username)
                self.assertIn("_auth_user_id", self.client.session)

    def test_unverified_account_cannot_log_in(self):
        make_student(email="b@kepler.ac.rw", is_email_verified=False)
        self.login("b@kepler.ac.rw")
        self.assertNotIn("_auth_user_id", self.client.session)


class EnsureAdminCommandTests(TestCase):
    def test_creates_admin_once(self):
        from unittest import mock
        from django.core.management import call_command
        env = {"DJANGO_ADMIN_EMAIL": "Admin@Kepler.ac.rw", "DJANGO_ADMIN_PASSWORD": PASSWORD}
        with mock.patch.dict("os.environ", env):
            call_command("ensure_admin", stdout=open("/dev/null", "w"))
            call_command("ensure_admin", stdout=open("/dev/null", "w"))
        admin = User.objects.get()
        self.assertTrue(admin.is_superuser and admin.is_staff and admin.is_email_verified)
        self.assertEqual(admin.email, "admin@kepler.ac.rw")

    def test_skips_without_env(self):
        from django.core.management import call_command
        call_command("ensure_admin", stdout=open("/dev/null", "w"))
        self.assertFalse(User.objects.exists())

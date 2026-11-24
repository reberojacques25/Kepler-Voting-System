from django.test import TestCase
from django.urls import reverse

from apps.elections.models import Election
from apps.elections.tests.factories import make_staff, make_student


class AdminAccessTests(TestCase):
    def test_students_cannot_open_admin_dashboard(self):
        self.client.force_login(make_student())
        response = self.client.get(reverse("dashboard:admin_overview"))
        self.assertRedirects(response, reverse("dashboard:student"))

    def test_students_cannot_block_other_students(self):
        victim = make_student(2)
        self.client.force_login(make_student(1))
        self.client.post(reverse("dashboard:admin_toggle_student", args=[victim.id]), {"action": "block"})
        victim.refresh_from_db()
        self.assertTrue(victim.can_vote)


class AdminStudentActionsTests(TestCase):
    def setUp(self):
        self.client.force_login(make_staff())

    def toggle(self, student, action):
        self.client.post(reverse("dashboard:admin_toggle_student", args=[student.id]), {"action": action})
        student.refresh_from_db()

    def test_block_and_unblock(self):
        student = make_student()
        self.toggle(student, "block")
        self.assertFalse(student.can_vote)
        self.toggle(student, "unblock")
        self.assertTrue(student.can_vote)

    def test_manual_verify_also_activates_account(self):
        student = make_student(is_active=False, is_email_verified=False)
        self.toggle(student, "verify")
        self.assertTrue(student.is_email_verified)
        self.assertTrue(student.is_active)


class AdminElectionFormTests(TestCase):
    def setUp(self):
        self.client.force_login(make_staff())
        self.url = reverse("dashboard:admin_election_create")

    def test_rejects_end_before_start(self):
        self.client.post(self.url, {
            "name": "Bad dates", "start_at": "2026-12-10T10:00", "end_at": "2026-12-01T10:00",
        })
        self.assertFalse(Election.objects.exists())

    def test_creates_valid_election(self):
        self.client.post(self.url, {
            "name": "Guild 2027", "start_at": "2027-03-01T08:00", "end_at": "2027-03-01T17:00",
            "is_published": "on",
        })
        self.assertTrue(Election.objects.filter(name="Guild 2027").exists())

    def test_form_times_are_kigali_time(self):
        self.client.post(self.url, {
            "name": "Guild 2027", "start_at": "2027-03-01T08:00", "end_at": "2027-03-01T17:00",
        })
        election = Election.objects.get()
        # 08:00 in Kigali (UTC+2) is 06:00 UTC
        self.assertEqual(election.start_at.utctimetuple().tm_hour, 6)

    def test_edit_rejects_end_before_start(self):
        self.client.post(self.url, {
            "name": "Guild 2027", "start_at": "2027-03-01T08:00", "end_at": "2027-03-01T17:00",
        })
        election = Election.objects.get()
        self.client.post(reverse("dashboard:admin_election_edit", args=[election.id]), {
            "name": "Guild 2027", "start_at": "2027-03-02T08:00", "end_at": "2027-03-01T08:00",
        })
        election.refresh_from_db()
        self.assertEqual(election.end_at.day, 1)
        self.assertEqual(election.start_at.day, 1)

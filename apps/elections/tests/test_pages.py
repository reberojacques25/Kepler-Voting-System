"""Smoke tests: every main page renders without a server error."""
from django.test import TestCase
from django.urls import reverse

from apps.elections.models import ElectionWinner
from .factories import make_candidate, make_open_election, make_position, make_staff, make_student


class PublicPagesTests(TestCase):
    def setUp(self):
        self.election = make_open_election()
        position = make_position(self.election)
        self.candidate = make_candidate(position)
        ElectionWinner.objects.create(election=self.election, position=position, candidate=self.candidate)

    def test_public_pages_render(self):
        urls = [
            reverse("core:home"),
            reverse("core:about"),
            reverse("accounts:login"),
            reverse("accounts:signup"),
            reverse("elections:elections_list"),
            reverse("elections:election_detail", args=[self.election.id]),
            reverse("elections:campaign_browse", args=[self.election.id]),
            reverse("elections:candidate_profile", args=[self.candidate.id]),
            reverse("history:guild_history"),
            reverse("history:council_detail", args=[self.election.id]),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_student_pages_render(self):
        self.client.force_login(make_student())
        for name in ["dashboard:student", "elections:open_positions", "elections:my_applications"]:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_admin_pages_render(self):
        self.client.force_login(make_staff())
        urls = [
            reverse("dashboard:admin_overview"),
            reverse("dashboard:admin_students"),
            reverse("dashboard:admin_cohorts"),
            reverse("dashboard:admin_elections"),
            reverse("dashboard:admin_election_manage", args=[self.election.id]),
            reverse("dashboard:admin_analytics"),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

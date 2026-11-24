from datetime import timedelta
from unittest import mock

from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.elections.models import Vote
from .factories import (
    PASSWORD, make_candidate, make_cohort, make_open_election, make_position, make_student,
)


class VotingRulesTests(TestCase):
    def setUp(self):
        self.election = make_open_election()
        self.position = make_position(self.election)
        self.alice = make_candidate(self.position, "Alice")
        self.bob = make_candidate(self.position, "Bob")
        self.student = make_student()
        self.client.force_login(self.student)
        self.url = reverse("elections:vote_position", args=[self.election.id, self.position.id])

    def vote(self, candidate):
        return self.client.post(self.url, {"candidate_id": candidate.id})

    def test_student_can_vote_once(self):
        self.vote(self.alice)
        self.assertEqual(Vote.objects.filter(voter=self.student).count(), 1)

    def test_second_vote_is_ignored(self):
        self.vote(self.alice)
        self.vote(self.bob)
        votes = Vote.objects.filter(voter=self.student)
        self.assertEqual(votes.count(), 1)
        self.assertEqual(votes.get().candidate, self.alice)

    def test_race_on_double_submit_does_not_crash(self):
        """Two near-simultaneous submits both pass the 'already voted' check;
        the DB constraint rejects one and the user must not see a 500."""
        with mock.patch("apps.elections.views.Vote.objects.create", side_effect=IntegrityError):
            response = self.vote(self.alice)
        self.assertEqual(response.status_code, 302)

    def test_blocked_student_cannot_vote(self):
        self.student.can_vote = False
        self.student.save()
        self.vote(self.alice)
        self.assertFalse(Vote.objects.exists())

    def test_unverified_student_cannot_vote(self):
        self.student.is_email_verified = False
        self.student.save()
        self.vote(self.alice)
        self.assertFalse(Vote.objects.exists())

    def test_cannot_vote_before_election_opens(self):
        self.election.start_at = timezone.now() + timedelta(days=1)
        self.election.end_at = timezone.now() + timedelta(days=2)
        self.election.save()
        self.vote(self.alice)
        self.assertFalse(Vote.objects.exists())

    def test_cannot_vote_after_election_closes(self):
        self.election.start_at = timezone.now() - timedelta(days=2)
        self.election.end_at = timezone.now() - timedelta(days=1)
        self.election.save()
        self.vote(self.alice)
        self.assertFalse(Vote.objects.exists())

    def test_cannot_vote_for_unapproved_candidate(self):
        pending = make_candidate(self.position, "Pending", status="pending")
        response = self.vote(pending)
        self.assertEqual(response.status_code, 404)
        self.assertFalse(Vote.objects.exists())

    def test_cannot_vote_for_candidate_of_another_position(self):
        other = make_position(self.election, "Secretary")
        carol = make_candidate(other, "Carol")
        response = self.vote(carol)
        self.assertEqual(response.status_code, 404)

    def test_anonymous_user_is_sent_to_login(self):
        self.client.logout()
        response = self.vote(self.alice)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)


class CohortRestrictionTests(TestCase):
    def setUp(self):
        self.cohort_a = make_cohort("Cohort A", 2024)
        self.cohort_b = make_cohort("Cohort B", 2025)
        self.election = make_open_election()
        self.position = make_position(self.election, voting_scope="cohort")
        self.position.allowed_cohorts.add(self.cohort_a)
        self.candidate = make_candidate(self.position)
        self.url = reverse("elections:vote_position", args=[self.election.id, self.position.id])

    def vote_as(self, student):
        self.client.force_login(student)
        self.client.post(self.url, {"candidate_id": self.candidate.id})

    def test_confirmed_member_of_allowed_cohort_can_vote(self):
        student = make_student(cohort=self.cohort_a, is_cohort_confirmed=True)
        self.vote_as(student)
        self.assertEqual(Vote.objects.count(), 1)

    def test_other_cohort_cannot_vote(self):
        student = make_student(cohort=self.cohort_b, is_cohort_confirmed=True)
        self.vote_as(student)
        self.assertFalse(Vote.objects.exists())

    def test_unconfirmed_cohort_cannot_vote(self):
        student = make_student(cohort=self.cohort_a, is_cohort_confirmed=False)
        self.vote_as(student)
        self.assertFalse(Vote.objects.exists())


class ResultsVisibilityTests(TestCase):
    def setUp(self):
        self.election = make_open_election()
        position = make_position(self.election)
        make_candidate(position)
        self.url = reverse("elections:results", args=[self.election.id])

    def test_results_hidden_while_open_without_live_results(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_results_shown_when_live_results_enabled(self):
        self.election.allow_live_results = True
        self.election.save()
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_results_shown_after_close(self):
        self.election.start_at = timezone.now() - timedelta(days=2)
        self.election.end_at = timezone.now() - timedelta(days=1)
        self.election.save()
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_live_json_forbidden_while_disabled(self):
        url = reverse("elections:live_results_json", args=[self.election.id])
        self.assertEqual(self.client.get(url).status_code, 403)

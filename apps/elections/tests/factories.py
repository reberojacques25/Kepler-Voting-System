from datetime import timedelta

from django.utils import timezone

from apps.accounts.models import Cohort, User
from apps.elections.models import Candidate, Election, Position

PASSWORD = "Str0ng-pass-123"


def make_student(n=1, **extra):
    defaults = dict(
        email=f"student{n}@kepler.ac.rw",
        student_id=f"KPL-{n:03d}",
        is_active=True,
        is_email_verified=True,
    )
    defaults.update(extra)
    user = User(**defaults)
    user.set_password(PASSWORD)
    user.save()
    return user


def make_staff():
    return make_student(999, is_staff=True)


def make_open_election(**extra):
    now = timezone.now()
    defaults = dict(name="Guild 2026", start_at=now - timedelta(hours=1), end_at=now + timedelta(hours=1))
    defaults.update(extra)
    return Election.objects.create(**defaults)


def make_position(election, title="President", **extra):
    return Position.objects.create(election=election, title=title, **extra)


def make_candidate(position, name="Alice", status="approved"):
    return Candidate.objects.create(
        election=position.election, position=position, full_name=name, status=status
    )


def make_cohort(name="Cohort 2025", year=2025):
    return Cohort.objects.create(name=name, year=year)

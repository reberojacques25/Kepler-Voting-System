from django.contrib.auth.models import AbstractUser
from django.db import models


class Cohort(models.Model):
    name = models.CharField(max_length=100, unique=True)
    year = models.PositiveIntegerField(help_text="Year this cohort started")

    class Meta:
        ordering = ['-year']

    def __str__(self):
        return self.name


class User(AbstractUser):
    email = models.EmailField(unique=True)
    student_id = models.CharField(max_length=20, unique=True)
    cohort = models.ForeignKey(
        Cohort,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students'
    )
    is_cohort_confirmed = models.BooleanField(
        default=False,
        help_text='Admin confirms the student belongs to the selected cohort'
    )
    is_email_verified = models.BooleanField(default=False)
    can_vote = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        if self.student_id:
            self.student_id = self.student_id.strip().upper()
        if not self.username:
            self.username = self.email or self.student_id
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.email} ({self.student_id})"
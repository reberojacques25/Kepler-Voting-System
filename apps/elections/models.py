from django.conf import settings
from django.db import models
from django.utils import timezone


class Election(models.Model):
    SCOPE_ALL = 'all'
    SCOPE_COHORT = 'cohort'
    SCOPE_CHOICES = [
        (SCOPE_ALL, 'Whole College'),
        (SCOPE_COHORT, 'Specific Cohort(s) Only'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    is_published = models.BooleanField(default=True)
    allow_live_results = models.BooleanField(default=False)

    visibility_scope = models.CharField(
        max_length=10, choices=SCOPE_CHOICES, default=SCOPE_ALL
    )
    visible_to_cohorts = models.ManyToManyField(
        'accounts.Cohort', blank=True, related_name='visible_elections'
    )
    voting_scope = models.CharField(
        max_length=10, choices=SCOPE_CHOICES, default=SCOPE_ALL
    )
    voting_cohorts = models.ManyToManyField(
        'accounts.Cohort', blank=True, related_name='voting_elections'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_at']

    def __str__(self):
        return self.name

    @property
    def is_open(self):
        now = timezone.now()
        return self.is_published and self.start_at <= now <= self.end_at

    @property
    def is_closed(self):
        return timezone.now() > self.end_at

    def student_can_see(self, user):
        if self.visibility_scope == self.SCOPE_ALL:
            return True
        if user.cohort is None:
            return False
        return self.visible_to_cohorts.filter(id=user.cohort.id).exists()

    def student_can_vote(self, user):
        if self.voting_scope == self.SCOPE_ALL:
            return True
        if user.cohort is None:
            return False
        return self.voting_cohorts.filter(id=user.cohort.id).exists()


class Position(models.Model):
    SCOPE_ALL = 'all'
    SCOPE_COHORT = 'cohort'
    SCOPE_CHOICES = [
        (SCOPE_ALL, 'Whole College'),
        (SCOPE_COHORT, 'Specific Cohort(s) Only'),
    ]

    election = models.ForeignKey(
        Election, on_delete=models.CASCADE, related_name='positions'
    )
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    voting_scope = models.CharField(
        max_length=10, choices=SCOPE_CHOICES, default=SCOPE_ALL
    )
    allowed_cohorts = models.ManyToManyField(
        'accounts.Cohort', blank=True, related_name='positions'
    )
    applications_open = models.BooleanField(default=False)

    class Meta:
        ordering = ['order', 'title']
        unique_together = [('election', 'title')]

    def __str__(self):
        return f"{self.title} — {self.election.name}"

    def student_can_vote(self, user):
        if self.voting_scope == self.SCOPE_ALL:
            return True
        if self.voting_scope == self.SCOPE_COHORT:
            if user.cohort is None:
                return False
            return self.allowed_cohorts.filter(id=user.cohort.id).exists()
        return False


class Candidate(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    election = models.ForeignKey(
        Election, on_delete=models.CASCADE, related_name='candidates'
    )
    position = models.ForeignKey(
        Position, on_delete=models.CASCADE, related_name='candidates'
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='candidacies'
    )
    full_name = models.CharField(max_length=200)
    slogan = models.CharField(max_length=200, blank=True)
    manifesto = models.TextField(blank=True)
    photo = models.ImageField(upload_to='candidates/', blank=True, null=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['position__order', 'full_name']

    def __str__(self):
        return f"{self.full_name} ({self.position.title})"


class PositionApplication(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    position = models.ForeignKey(
        Position, on_delete=models.CASCADE, related_name='applications'
    )
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='applications'
    )
    why_running = models.TextField()
    manifesto = models.TextField()
    slogan = models.CharField(max_length=200, blank=True)
    photo = models.ImageField(
        upload_to='applications/',
        blank=True,
        null=True,
        help_text='Profile photo for campaign use'
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending'
    )
    applied_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviewed_applications'
    )
    candidate = models.OneToOneField(
        Candidate,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='application'
    )

    class Meta:
        ordering = ['-applied_at']
        unique_together = [('position', 'applicant')]

    def __str__(self):
        return f"{self.applicant} → {self.position.title}"


class ApplicationField(models.Model):
    """Admin-defined custom questions for a position's application form."""
    FIELD_TEXT = 'text'
    FIELD_TEXTAREA = 'textarea'
    FIELD_FILE = 'file'
    FIELD_URL = 'url'
    FIELD_TYPES = [
        (FIELD_TEXT, 'Short Text'),
        (FIELD_TEXTAREA, 'Long Text / Paragraph'),
        (FIELD_FILE, 'File Upload'),
        (FIELD_URL, 'URL / Link'),
    ]

    position = models.ForeignKey(
        Position, on_delete=models.CASCADE, related_name='application_fields'
    )
    label = models.CharField(
        max_length=200,
        help_text='The question shown to students e.g. "Why do you want to run?"'
    )
    field_type = models.CharField(
        max_length=20, choices=FIELD_TYPES, default=FIELD_TEXTAREA
    )
    is_required = models.BooleanField(default=True)
    help_text = models.CharField(
        max_length=300, blank=True,
        help_text='Optional hint shown below the field'
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.label} ({self.position.title})"


class ApplicationAnswer(models.Model):
    """Student's answer to a custom application field."""
    application = models.ForeignKey(
        PositionApplication,
        on_delete=models.CASCADE,
        related_name='answers'
    )
    field = models.ForeignKey(
        ApplicationField,
        on_delete=models.CASCADE,
        related_name='answers'
    )
    value = models.TextField(blank=True)
    file = models.FileField(
        upload_to='application_answers/', blank=True, null=True
    )

    class Meta:
        unique_together = [('application', 'field')]

    def __str__(self):
        return f"{self.application} — {self.field.label}"


class CampaignPost(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    candidate = models.ForeignKey(
        Candidate, on_delete=models.CASCADE, related_name='campaign_posts'
    )
    title = models.CharField(max_length=200)
    content = models.TextField(blank=True)
    image = models.ImageField(upload_to='campaigns/', blank=True, null=True)
    link = models.URLField(blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} — {self.candidate.full_name}"


class Vote(models.Model):
    voter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, related_name='votes'
    )
    election = models.ForeignKey(
        Election, on_delete=models.CASCADE, related_name='votes'
    )
    position = models.ForeignKey(
        Position, on_delete=models.CASCADE, related_name='votes'
    )
    candidate = models.ForeignKey(
        Candidate, on_delete=models.CASCADE, related_name='votes'
    )
    cast_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('voter', 'election', 'position')]
        indexes = [
            models.Index(fields=['election', 'position']),
            models.Index(fields=['election', 'candidate']),
        ]

    def __str__(self):
        return f"{self.voter} -> {self.candidate} [{self.election}]"


class ElectionWinner(models.Model):
    election = models.ForeignKey(
        Election, on_delete=models.CASCADE, related_name='winners'
    )
    position = models.ForeignKey(
        Position, on_delete=models.CASCADE, related_name='winners'
    )
    candidate = models.ForeignKey(
        Candidate, on_delete=models.CASCADE, related_name='wins'
    )
    declared_at = models.DateTimeField(auto_now_add=True)
    declared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='declarations'
    )

    class Meta:
        unique_together = [('election', 'position')]
        ordering = ['-declared_at']

    def __str__(self):
        return f"{self.candidate.full_name} — {self.position.title} ({self.election.name})"


class Achievement(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    winner = models.ForeignKey(
        ElectionWinner, on_delete=models.CASCADE, related_name='achievements'
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviewed_achievements'
    )

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.title} — {self.winner.candidate.full_name} ({self.status})"
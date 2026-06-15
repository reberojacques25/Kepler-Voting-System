from django.contrib import admin
from .models import (
    Election, Position, Candidate, CampaignPost,
    Vote, PositionApplication, ElectionWinner, Achievement
)

@admin.register(Election)
class ElectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_at', 'end_at', 'is_published']

@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ['title', 'election', 'voting_scope', 'applications_open']
    filter_horizontal = ['allowed_cohorts']

@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'position', 'election', 'status']
    list_filter = ['status', 'election']

@admin.register(PositionApplication)
class PositionApplicationAdmin(admin.ModelAdmin):
    list_display = ['applicant', 'position', 'status', 'applied_at']
    list_filter = ['status']

@admin.register(ElectionWinner)
class ElectionWinnerAdmin(admin.ModelAdmin):
    list_display = ['candidate', 'position', 'election', 'declared_by', 'declared_at']

@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ['title', 'winner', 'status', 'submitted_at']
    list_filter = ['status']

@admin.register(CampaignPost)
class CampaignPostAdmin(admin.ModelAdmin):
    list_display = ['title', 'candidate', 'created_at']
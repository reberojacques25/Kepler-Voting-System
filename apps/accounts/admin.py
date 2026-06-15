from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Cohort

@admin.register(Cohort)
class CohortAdmin(admin.ModelAdmin):
    list_display = ['name', 'year']

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['email', 'student_id', 'cohort', 'is_email_verified', 'can_vote']
    list_filter = ['cohort', 'is_email_verified', 'can_vote']
    fieldsets = UserAdmin.fieldsets + (
        ('Kepler Info', {'fields': ('student_id', 'cohort', 'is_email_verified', 'can_vote')}),
    )
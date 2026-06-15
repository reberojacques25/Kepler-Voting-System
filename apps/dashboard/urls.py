from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.student, name='student'),
    path('admin/', views.admin_overview, name='admin_overview'),

    # Students
    path('admin/students/', views.admin_students, name='admin_students'),
    path('admin/students/<int:student_id>/toggle/', views.admin_toggle_student, name='admin_toggle_student'),

    # Cohorts
    path('admin/cohorts/', views.admin_cohorts, name='admin_cohorts'),
    path('admin/cohorts/add/', views.admin_cohort_create, name='admin_cohort_create'),
    path('admin/cohorts/<int:cohort_id>/edit/', views.admin_cohort_edit, name='admin_cohort_edit'),
    path('admin/cohorts/<int:cohort_id>/delete/', views.admin_cohort_delete, name='admin_cohort_delete'),

    # Elections
    path('admin/elections/', views.admin_elections, name='admin_elections'),
    path('admin/elections/create/', views.admin_election_create, name='admin_election_create'),
    path('admin/elections/<int:election_id>/edit/', views.admin_election_edit, name='admin_election_edit'),
    path('admin/elections/<int:election_id>/delete/', views.admin_election_delete, name='admin_election_delete'),
    path('admin/elections/<int:election_id>/manage/', views.admin_election_manage, name='admin_election_manage'),
    path('admin/elections/<int:election_id>/export.csv', views.export_election_results_csv, name='export_election_results_csv'),
    path('admin/elections/<int:election_id>/export.pdf', views.export_election_results_pdf, name='export_election_results_pdf'),

    # Positions
    path('admin/elections/<int:election_id>/positions/add/', views.admin_position_create, name='admin_position_create'),
    path('admin/elections/<int:election_id>/positions/<int:position_id>/edit/', views.admin_position_edit, name='admin_position_edit'),
    path('admin/elections/<int:election_id>/positions/<int:position_id>/delete/', views.admin_position_delete, name='admin_position_delete'),
    path('admin/elections/<int:election_id>/positions/<int:position_id>/toggle-applications/', views.admin_position_toggle_applications, name='admin_position_toggle_applications'),

    # Application Fields
    path('admin/elections/<int:election_id>/positions/<int:position_id>/fields/', views.admin_position_fields, name='admin_position_fields'),
    path('admin/elections/<int:election_id>/positions/<int:position_id>/fields/add/', views.admin_field_create, name='admin_field_create'),
    path('admin/elections/<int:election_id>/positions/<int:position_id>/fields/<int:field_id>/edit/', views.admin_field_edit, name='admin_field_edit'),
    path('admin/elections/<int:election_id>/positions/<int:position_id>/fields/<int:field_id>/delete/', views.admin_field_delete, name='admin_field_delete'),

    # Candidates
    path('admin/candidates/', views.admin_candidates, name='admin_candidates'),
    path('admin/candidates/<int:application_id>/', views.admin_application_detail, name='admin_application_detail'),
    path('admin/candidates/<int:application_id>/review/', views.admin_application_review, name='admin_application_review'),

    # Campaigns
    path('admin/campaigns/', views.admin_campaigns, name='admin_campaigns'),
    path('admin/campaigns/<int:post_id>/review/', views.admin_campaign_review, name='admin_campaign_review'),

    # Declare Winners
    path('admin/elections/<int:election_id>/declare-winners/', views.admin_declare_winners, name='admin_declare_winners'),
    path('admin/elections/<int:election_id>/positions/<int:position_id>/declare-winner/', views.admin_declare_winner_save, name='admin_declare_winner_save'),
    path('admin/elections/<int:election_id>/positions/<int:position_id>/undeclare-winner/', views.admin_undeclare_winner, name='admin_undeclare_winner'),

    # Achievements
    path('admin/achievements/', views.admin_achievements, name='admin_achievements'),
    path('admin/achievements/<int:achievement_id>/review/', views.admin_achievement_review, name='admin_achievement_review'),
    path('my-achievements/', views.my_achievements, name='my_achievements'),

    # Analytics
    path('admin/analytics/', views.admin_analytics, name='admin_analytics'),
]
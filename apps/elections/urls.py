from django.urls import path
from . import views

app_name = 'elections'

urlpatterns = [
    path('', views.elections_list, name='elections_list'),
    path('<int:election_id>/', views.election_detail, name='election_detail'),
    path('<int:election_id>/results/', views.results, name='results'),
    path('<int:election_id>/live.json', views.live_results_json, name='live_results_json'),
    path('<int:election_id>/positions/<int:position_id>/vote/', views.vote_position, name='vote_position'),
    path('<int:election_id>/campaigns/', views.campaign_browse, name='campaign_browse'),
    path('candidates/<int:candidate_id>/', views.candidate_profile, name='candidate_profile'),
    path('apply/', views.open_positions, name='open_positions'),
    path('<int:election_id>/positions/<int:position_id>/apply/', views.apply_position, name='apply_position'),
    path('my-applications/', views.my_applications, name='my_applications'),
    path('my-campaign/', views.my_campaign, name='my_campaign'),
    path('my-campaign/<int:candidate_id>/post/', views.campaign_post_create, name='campaign_post_create'),
    path('my-campaign/post/<int:post_id>/delete/', views.campaign_post_delete, name='campaign_post_delete'),
]
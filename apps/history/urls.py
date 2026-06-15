from django.urls import path
from . import views

app_name = 'history'

urlpatterns = [
    path('', views.guild_history, name='guild_history'),
    path('<int:election_id>/', views.council_detail, name='council_detail'),
]
from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("zones/", views.zones_view, name="zones"),
    path("enter_zone/", views.enter_zone, name="enter_zone"),
    path("zone/<int:zone_id>/play/", views.zone_play, name="zone_play"),
    path("zone/<int:zone_id>/submit/", views.submit_zone, name="submit_zone"),
    path("login/", views.team_login, name="team_login"),
    path("logout/", views.team_logout, name="logout"),
    path("leaderboard/", views.leaderboard_view, name="leaderboard"),

]
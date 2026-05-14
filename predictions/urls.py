from django.urls import path

from . import views

app_name = "predictions"

urlpatterns = [
    path("", views.home, name="home"),
    path("api/today-matches/", views.matches_today_json, name="matches_today_json"),
    path("search/", views.global_search, name="search"),
    path("player/<int:player_id>/", views.player_detail, name="player_detail"),
    path("team/<str:team_code>/", views.team_detail, name="team_detail"),
    path("wc/groups/", views.wc_groups_index, name="wc_groups"),
    path("wc/group/<str:letter>/", views.wc_group_detail, name="wc_group"),
    path("insights/", views.insights_hub, name="insights"),
    path("fixtures/", views.fixtures_hub, name="fixtures_hub"),
    path("sources/", views.sources, name="sources"),
    # path (not str) so round names may contain "/" without breaking {% url %} / reverse().
    path("round/<path:round_name>/", views.round_detail, name="round"),
    path("match/<int:match_id>/", views.match_detail, name="match_detail"),
    path("match/<int:match_id>/run-agent/", views.run_agent, name="run_agent"),
    path("match/<int:match_id>/run-stub/", views.run_stub, name="run_stub"),
]

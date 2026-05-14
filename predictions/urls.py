from django.urls import path

from . import views

app_name = "predictions"

urlpatterns = [
    path("", views.home, name="home"),
    path("fixtures/", views.fixtures_hub, name="fixtures_hub"),
    path("sources/", views.sources, name="sources"),
    path("round/<str:round_name>/", views.round_detail, name="round"),
    path("match/<int:match_id>/", views.match_detail, name="match_detail"),
    path("match/<int:match_id>/run-agent/", views.run_agent, name="run_agent"),
    path("match/<int:match_id>/run-stub/", views.run_stub, name="run_stub"),
]

from django.contrib import admin

from predictions.models import PredictionSnapshot

from .models import Match, Player, Team


class PredictionSnapshotInline(admin.TabularInline):
    model = PredictionSnapshot
    extra = 0
    readonly_fields = ("created_at",)
    fields = ("created_at", "pred_home_goals", "pred_away_goals", "confidence", "change_explanation")


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "group_label")
    search_fields = ("name", "code")


class PlayerInline(admin.TabularInline):
    model = Player
    extra = 0


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ("name", "team", "position", "shirt_number", "is_injured")
    list_filter = ("team", "is_injured", "position")
    search_fields = ("name", "team__name", "performance_summary", "club")
    fieldsets = (
        (None, {"fields": ("team", "name", "position", "shirt_number", "club")}),
        ("Availability", {"fields": ("is_injured", "injury_notes", "cards_suspension_notes")}),
        ("Form & stats (fed to the AI)", {"fields": ("form_notes", "recent_club_scores", "performance_summary", "stats_snapshot")}),
    )


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    inlines = [PredictionSnapshotInline]
    list_display = (
        "round_name",
        "home_team",
        "away_team",
        "is_world_cup",
        "competition_display",
        "status",
        "kickoff",
        "home_score",
        "away_score",
    )
    list_filter = ("status", "round_name", "is_world_cup")
    search_fields = ("home_team__name", "away_team__name", "round_name")

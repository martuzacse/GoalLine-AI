from django.contrib import admin

from predictions.models import PredictionSnapshot

from .models import KnockoutFeed, Match, MatchEvent, NewsFeedItem, Player, Team


class KnockoutFeedInline(admin.TabularInline):
    model = KnockoutFeed
    fk_name = "target_match"
    extra = 0
    fields = ("target_side", "source_match")
    verbose_name_plural = "Knockout bracket feeds (fill a side from winner of source match)"


class PredictionSnapshotInline(admin.TabularInline):
    model = PredictionSnapshot
    extra = 0
    readonly_fields = ("created_at",)
    fields = ("created_at", "pred_home_goals", "pred_away_goals", "confidence", "change_explanation")


class MatchEventInline(admin.TabularInline):
    model = MatchEvent
    extra = 0
    fields = ("minute", "event_type", "side", "headline", "detail")


@admin.register(MatchEvent)
class MatchEventAdmin(admin.ModelAdmin):
    list_display = ("match", "minute", "event_type", "side", "headline")
    list_filter = ("event_type", "side")
    search_fields = ("headline", "detail", "match__round_name")


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


@admin.register(KnockoutFeed)
class KnockoutFeedAdmin(admin.ModelAdmin):
    list_display = ("target_match", "target_side", "source_match")
    list_filter = ("target_side",)
    search_fields = ("target_match__round_name", "source_match__round_name")


@admin.register(NewsFeedItem)
class NewsFeedItemAdmin(admin.ModelAdmin):
    list_display = ("title", "source", "fetched_at", "url")
    readonly_fields = ("fetched_at",)


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    inlines = [KnockoutFeedInline, MatchEventInline, PredictionSnapshotInline]
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
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "round_name",
                    "home_team",
                    "away_team",
                    "kickoff",
                    "status",
                    "home_score",
                    "away_score",
                    "is_world_cup",
                    "competition_display",
                )
            },
        ),
        ("Tactics & narrative", {"fields": ("tactical_notes_home", "tactical_notes_away", "external_news_digest", "prematch_brief")}),
        ("Lineups (JSON lists)", {"fields": ("lineup_home", "lineup_away")}),
    )

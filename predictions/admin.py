from django.contrib import admin

from .models import PredictionSnapshot


@admin.register(PredictionSnapshot)
class PredictionSnapshotAdmin(admin.ModelAdmin):
    list_display = ("match", "scoreline_label", "confidence", "created_at", "supersedes_id")
    list_filter = ("match__round_name",)
    search_fields = ("match__home_team__name", "match__away_team__name")
    readonly_fields = ("created_at", "raw_model_response", "predicted_scorers")

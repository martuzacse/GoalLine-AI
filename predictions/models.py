from django.db import models


class PredictionSnapshot(models.Model):
    """One agent output for a match; newest row explains deltas via change_explanation."""

    match = models.ForeignKey("matches.Match", on_delete=models.CASCADE, related_name="prediction_snapshots")
    created_at = models.DateTimeField(auto_now_add=True)
    pred_home_goals = models.PositiveSmallIntegerField()
    pred_away_goals = models.PositiveSmallIntegerField()
    confidence = models.PositiveSmallIntegerField(
        help_text="0–100: model-estimated probability the scoreline bucket is roughly right"
    )
    reasoning = models.TextField(help_text="Full narrative: squads, form, injuries, tactics, news.")
    factors = models.JSONField(default=dict, blank=True, help_text="Structured breakdown for the UI.")
    source_digest = models.TextField(
        blank=True,
        help_text="What context was supplied (squads, scores, news digest) before the call.",
    )
    supersedes = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="superseded_by",
    )
    change_explanation = models.TextField(
        blank=True,
        help_text="If this replaces a prior snapshot, why the prediction moved.",
    )
    raw_model_response = models.TextField(blank=True, editable=False)
    predicted_scorers = models.JSONField(
        default=dict,
        blank=True,
        help_text='Shape: {"home":[{"player","rationale","confidence?"}...], "away":[...], "summary"?}',
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.match_id}: {self.pred_home_goals}-{self.pred_away_goals} @ {self.created_at:%Y-%m-%d %H:%M}"

    @property
    def scoreline_label(self) -> str:
        return f"{self.pred_home_goals}–{self.pred_away_goals}"

    @classmethod
    def latest_by_match_id(cls, match_ids: list[int]) -> dict[int, "PredictionSnapshot"]:
        """Most recent snapshot per match id (one query)."""
        if not match_ids:
            return {}
        out: dict[int, PredictionSnapshot] = {}
        for snap in cls.objects.filter(match_id__in=match_ids).order_by("match_id", "-created_at"):
            if snap.match_id not in out:
                out[snap.match_id] = snap
        return out

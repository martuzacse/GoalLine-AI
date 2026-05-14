from django.db import models


class Team(models.Model):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=8, unique=True, help_text="FIFA-style short code, e.g. BRA")
    group_label = models.CharField(max_length=16, blank=True, help_text="e.g. A, B, or empty for knockout-only")

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class Player(models.Model):
    class Position(models.TextChoices):
        GK = "GK", "Goalkeeper"
        DF = "DF", "Defender"
        MF = "MF", "Midfielder"
        FW = "FW", "Forward"

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="players")
    name = models.CharField(max_length=120)
    position = models.CharField(max_length=2, choices=Position.choices, default=Position.MF)
    club = models.CharField(max_length=160, blank=True)
    is_injured = models.BooleanField(default=False)
    injury_notes = models.CharField(max_length=255, blank=True)
    cards_suspension_notes = models.CharField(max_length=255, blank=True)
    form_notes = models.CharField(max_length=500, blank=True, help_text="Recent performance / media narrative")
    shirt_number = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Squad number when known (FIFA / federation list).",
    )
    recent_club_scores = models.CharField(
        max_length=120,
        blank=True,
        help_text="Compact recent results you curate (e.g. last 5 club: W W L D W). Not auto-scraped.",
    )
    performance_summary = models.TextField(
        blank=True,
        help_text="Short curator summary: minutes, goals/assists trend, NT form — fed to the prediction agent.",
    )
    stats_snapshot = models.JSONField(
        default=dict,
        blank=True,
        help_text="Optional structured stats (goals, assists, xG string, apps) for the agent; keep small.",
    )

    class Meta:
        ordering = ["team", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.team.code})"


class Match(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        LIVE = "live", "Live"
        FINISHED = "finished", "Finished"

    round_name = models.CharField(max_length=80, help_text="e.g. Group A – Matchday 1, Round of 16")
    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="home_fixtures")
    away_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="away_fixtures")
    kickoff = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.SCHEDULED)
    home_score = models.PositiveSmallIntegerField(null=True, blank=True)
    away_score = models.PositiveSmallIntegerField(null=True, blank=True)
    tactical_notes_home = models.TextField(blank=True)
    tactical_notes_away = models.TextField(blank=True)
    external_news_digest = models.TextField(
        blank=True,
        help_text="Paste or sync summaries from news sites; fed to the agent as context.",
    )
    is_world_cup = models.BooleanField(
        default=True,
        db_index=True,
        help_text="If true, match appears under the World Cup hub; otherwise under Current competitions.",
    )
    competition_display = models.CharField(
        max_length=80,
        blank=True,
        help_text="Short label for the fixtures strip (e.g. Premier League, MLS).",
    )
    lineup_home = models.JSONField(
        default=list,
        blank=True,
        help_text='Optional XI: list of strings or objects, e.g. ["#9 R. Lewandowski", …]',
    )
    lineup_away = models.JSONField(
        default=list,
        blank=True,
        help_text="Optional XI for the away side (same shape as lineup_home).",
    )
    prematch_brief = models.TextField(
        blank=True,
        help_text="Curated one-screen brief (form, injuries, stakes) shown on the public match page.",
    )

    class Meta:
        ordering = ["kickoff", "id"]
        verbose_name_plural = "matches"

    def __str__(self) -> str:
        return f"{self.home_team.code} vs {self.away_team.code} ({self.round_name})"


class MatchEvent(models.Model):
    """Curated timeline rows (goals, cards, subs, notes) for richer match pages."""

    class EventType(models.TextChoices):
        GOAL = "goal", "Goal"
        OWN_GOAL = "own_goal", "Own goal"
        CARD_YELLOW = "card_yellow", "Yellow card"
        CARD_RED = "card_red", "Red card"
        SUB = "sub", "Substitution"
        PENALTY = "penalty", "Penalty"
        NOTE = "note", "Note"
        OTHER = "other", "Other"

    class Side(models.TextChoices):
        HOME = "home", "Home"
        AWAY = "away", "Away"
        NEUTRAL = "neutral", "Neutral"

    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="events")
    minute = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Match minute, if known.")
    event_type = models.CharField(max_length=20, choices=EventType.choices, default=EventType.NOTE)
    side = models.CharField(max_length=10, choices=Side.choices, default=Side.NEUTRAL)
    headline = models.CharField(max_length=200)
    detail = models.TextField(blank=True)

    class Meta:
        ordering = ["minute", "id"]

    def __str__(self) -> str:
        mm = f"{self.minute}' " if self.minute is not None else ""
        return f"{mm}{self.get_event_type_display()}: {self.headline}"


class KnockoutFeed(models.Model):
    """Links a knockout match side to a source match whose winner (or predicted winner) fills the slot."""

    class Side(models.TextChoices):
        HOME = "home", "Home"
        AWAY = "away", "Away"

    target_match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="knockout_feeds_in")
    target_side = models.CharField(max_length=4, choices=Side.choices)
    source_match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="knockout_feeds_out")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["target_match", "target_side"],
                name="uniq_knockout_feed_target_side",
            )
        ]

    def __str__(self) -> str:
        return f"{self.target_match_id} {self.target_side} ← winner of {self.source_match_id}"


class NewsFeedItem(models.Model):
    """Cached headlines (e.g. from Goal.com US) for the home page."""

    title = models.CharField(max_length=400)
    url = models.URLField(max_length=600, blank=True)
    source = models.CharField(max_length=40, default="goal.com")
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fetched_at"]

    def __str__(self) -> str:
        return self.title[:80]

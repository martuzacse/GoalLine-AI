from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from matches.models import Match, Player, Team
from predictions.models import PredictionSnapshot


class Command(BaseCommand):
    help = "Load a small demo dataset (teams, players, matches)."

    def handle(self, *args, **options):
        Team.objects.all().delete()
        t_bra = Team.objects.create(name="Brazil", code="BRA", group_label="G")
        t_arg = Team.objects.create(name="Argentina", code="ARG", group_label="G")
        t_fra = Team.objects.create(name="France", code="FRA", group_label="D")
        t_ger = Team.objects.create(name="Germany", code="GER", group_label="D")
        t_liv = Team.objects.create(name="Liverpool", code="LIV", group_label="")
        t_mci = Team.objects.create(name="Manchester City", code="MCI", group_label="")
        t_ars = Team.objects.create(name="Arsenal", code="ARS", group_label="")

        Player.objects.create(
            team=t_bra,
            name="Demo Forward A",
            position=Player.Position.FW,
            club="Demo FC",
            form_notes="Strong club season; press highlights positive fitness.",
        )
        Player.objects.create(
            team=t_bra,
            name="Demo Mid B",
            position=Player.Position.MF,
            is_injured=True,
            injury_notes="Knock reported in training camp — day-to-day.",
        )
        Player.objects.create(
            team=t_arg,
            name="Demo Star C",
            position=Player.Position.FW,
            form_notes="Mixed friendly performances.",
        )
        Player.objects.create(
            team=t_fra,
            name="Demo Defender D",
            position=Player.Position.DF,
            cards_suspension_notes="Carries yellow into knockout risk.",
        )

        now = timezone.now()
        m1 = Match.objects.create(
            round_name="Group stage – MD1",
            home_team=t_bra,
            away_team=t_arg,
            kickoff=now,
            status=Match.Status.SCHEDULED,
            is_world_cup=True,
            competition_display="2026 FIFA World Cup",
            tactical_notes_home="High press with inverted fullbacks.",
            tactical_notes_away="Compact mid-block; quick transitions.",
            external_news_digest=(
                "Sample digest: both sides arrived with full squads in camp; "
                "one Brazil midfielder flagged as doubtful in local press."
            ),
        )
        Match.objects.create(
            round_name="Group stage – MD1",
            home_team=t_fra,
            away_team=t_ger,
            kickoff=now,
            status=Match.Status.SCHEDULED,
            is_world_cup=True,
            competition_display="2026 FIFA World Cup",
            tactical_notes_home="4231, wide overloads.",
            tactical_notes_away="352 with aggressive wingbacks.",
        )
        Match.objects.create(
            round_name="Round of 16",
            home_team=t_bra,
            away_team=t_ger,
            kickoff=now + timedelta(days=14),
            status=Match.Status.SCHEDULED,
            is_world_cup=True,
            competition_display="2026 FIFA World Cup",
            tactical_notes_home="Knockout tempo; wider rotations.",
            tactical_notes_away="Low block with fast wingers.",
        )

        Match.objects.create(
            round_name="MW 35 · demo",
            home_team=t_liv,
            away_team=t_mci,
            kickoff=now,
            status=Match.Status.LIVE,
            home_score=1,
            away_score=1,
            is_world_cup=False,
            competition_display="Premier League (demo)",
            tactical_notes_home="High line; fullbacks tuck inside.",
            tactical_notes_away="Control possession; overload left.",
        )
        Match.objects.create(
            round_name="MW 35 · demo",
            home_team=t_ars,
            away_team=t_liv,
            kickoff=now + timedelta(days=1),
            status=Match.Status.SCHEDULED,
            is_world_cup=False,
            competition_display="Premier League (demo)",
            tactical_notes_home="Press after loss; quick switches.",
            tactical_notes_away="Compact 4-4-2 mid-block.",
        )

        PredictionSnapshot.objects.create(
            match=m1,
            pred_home_goals=2,
            pred_away_goals=1,
            confidence=58,
            reasoning=(
                "Initial seeded prediction: Brazil depth vs Argentina structure; "
                "replace by running the agent from the match page."
            ),
            factors={"seed": ["bootstrap row for UI timeline demo"]},
            predicted_scorers={
                "summary": "Seeded example: home pressure and wide overloads create chances.",
                "home": [
                    {
                        "player": "Demo Forward A",
                        "rationale": "Primary outlet in transition; strong club form in seed data.",
                        "confidence": 52,
                    },
                    {
                        "player": "Demo Forward A",
                        "rationale": "Second goal from a set-piece secondary run (brace scenario demo).",
                        "confidence": 28,
                    },
                ],
                "away": [
                    {
                        "player": "Demo Star C",
                        "rationale": "Argentina’s main carrier in the half-spaces against a high line.",
                        "confidence": 41,
                    },
                ],
            },
            source_digest="(seeded — not from DeepSeek)",
        )

        self.stdout.write(self.style.SUCCESS("Demo data created. Visit /fixtures/?tab=worldcup or run python manage.py load_wc2026_fixtures --replace-wc for the full group stage."))

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from matches.models import Match, Team
from matches.wc2026_data import all_codes, all_team_rows, iter_group_stage_rows


class Command(BaseCommand):
    help = (
        "Load all 2026 FIFA World Cup *group-stage* matches (72) from the post-draw lineup. "
        "Kickoffs are evenly spaced placeholders (UTC) until you sync real times from FIFA’s "
        "official schedule page. Knock-out ties are bracket-dependent and are not auto-generated."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--replace-wc",
            action="store_true",
            help="Delete existing World Cup matches (is_world_cup=True) before loading.",
        )

    def handle(self, *args, **options):
        replace = options["replace_wc"]
        if not replace:
            self.stderr.write(
                "Refusing to run without --replace-wc (prevents accidental duplicate rows). "
                "Re-run with: python manage.py load_wc2026_fixtures --replace-wc"
            )
            return

        with transaction.atomic():
            total_deleted, _ = Match.objects.filter(is_world_cup=True).delete()
            self.stdout.write(
                self.style.WARNING(f"Removed {total_deleted} existing World Cup rows (matches + cascaded data).")
            )

            created_teams = 0
            updated_teams = 0
            for code, name, letter in all_team_rows():
                _, was_created = Team.objects.update_or_create(
                    code=code,
                    defaults={"name": name, "group_label": letter},
                )
                if was_created:
                    created_teams += 1
                else:
                    updated_teams += 1

            matches_created = 0
            team_by_code = {
                t.code: t for t in Team.objects.filter(code__in=sorted(all_codes()))
            }
            for row in iter_group_stage_rows():
                home = team_by_code[row.home_code]
                away = team_by_code[row.away_code]
                Match.objects.create(
                    round_name=row.round_name,
                    home_team=home,
                    away_team=away,
                    kickoff=row.kickoff,
                    status=Match.Status.SCHEDULED,
                    is_world_cup=True,
                    competition_display="2026 FIFA World Cup",
                )
                matches_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"World Cup group stage loaded: {matches_created} matches, "
                f"{created_teams} teams created, {updated_teams} teams updated."
            )
        )
        self.stdout.write(
            self.style.NOTICE(
                "If you had knockout placeholders, re-run: python manage.py load_wc2026_knockout --force"
            )
        )
        self.stdout.write(
            "Next: curate squads (names, positions, recent form) with "
            "`python manage.py import_squad_json --file matches/data/wc2026_squads_sample.json` "
            "or your own JSON following the same schema."
        )

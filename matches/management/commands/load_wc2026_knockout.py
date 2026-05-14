from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from matches.models import Match, Team
from matches.wc2026_knockout import (
    KO_ROUND_SPECS,
    bracket_placeholder_code,
    first_knockout_kickoff_utc,
    iter_knockout_placeholder_rows,
)


def _ko_round_names() -> set[str]:
    return {name for name, _ in KO_ROUND_SPECS}


class Command(BaseCommand):
    help = (
        "Append 2026 World Cup knockout placeholder matches (Round of 32 through Final). "
        "Uses placeholder teams (codes Q0000001…). Wire real bracket paths via KnockoutFeed in admin "
        "and run resolve_knockout_bracket. Does not remove group-stage rows."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--force",
            action="store_true",
            help="Delete existing WC matches whose round_name is a known knockout phase, then reload.",
        )

    def handle(self, *args, **options):
        force: bool = options["force"]
        ko_names = _ko_round_names()

        existing_final = Match.objects.filter(is_world_cup=True, round_name="Final").exists()
        if existing_final and not force:
            self.stderr.write(
                self.style.WARNING(
                    "Knockout rows already present. Re-run with --force to delete knockout-phase "
                    "matches and reload (group stage untouched)."
                )
            )
            return

        base = first_knockout_kickoff_utc()
        from datetime import timedelta

        with transaction.atomic():
            if force:
                deleted, _ = Match.objects.filter(is_world_cup=True, round_name__in=ko_names).delete()
                self.stdout.write(self.style.WARNING(f"Removed {deleted} knockout-phase match rows."))

            # Placeholder teams for every slot used by iter_knockout_placeholder_rows (64 slots).
            for i in range(1, 65):
                code = bracket_placeholder_code(i)
                Team.objects.update_or_create(
                    code=code,
                    defaults={
                        "name": f"Bracket slot {i} (TBD)",
                        "group_label": "",
                    },
                )

            codes = [bracket_placeholder_code(i) for i in range(1, 65)]
            team_by_code = {t.code: t for t in Team.objects.filter(code__in=codes)}

            n = 0
            for row in iter_knockout_placeholder_rows():
                kick = base + timedelta(hours=row.kickoff_index)
                hc = bracket_placeholder_code(row.home_slot)
                ac = bracket_placeholder_code(row.away_slot)
                Match.objects.create(
                    round_name=row.round_name,
                    home_team=team_by_code[hc],
                    away_team=team_by_code[ac],
                    kickoff=kick,
                    status=Match.Status.SCHEDULED,
                    is_world_cup=True,
                    competition_display="2026 FIFA World Cup",
                )
                n += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Knockout placeholders created: {n} matches. "
                "Add KnockoutFeed rows (target side ← source match) then: "
                "python manage.py resolve_knockout_bracket"
            )
        )

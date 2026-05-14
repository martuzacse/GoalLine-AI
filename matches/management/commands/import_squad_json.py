from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from matches.squad_import import SquadImportError, import_squad_json_file


class Command(BaseCommand):
    help = (
        "Import national-team squads from a JSON file into Player rows (positions, club, "
        "recent results text, performance summary, stats_snapshot). "
        "This does NOT scrape Goal.com or FIFA HTML — use official squad PDFs, federation CSVs, "
        "or licensed APIs, then shape data to the sample schema in matches/data/wc2026_squads_sample.json."
    )

    def add_arguments(self, parser) -> None:
        root = Path(settings.BASE_DIR) / "matches" / "data" / "wc2026_squads_sample.json"
        parser.add_argument(
            "--file",
            type=str,
            default=str(root),
            help="Path to JSON object keyed by team code (e.g. BRA) -> list of player objects.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate file and team codes without writing to the database.",
        )

    def handle(self, *args, **options):
        path = Path(options["file"]).expanduser().resolve()
        if not path.is_file():
            raise SystemExit(f"File not found: {path}")

        try:
            created, updated, warnings = import_squad_json_file(path, dry_run=options["dry_run"])
        except (SquadImportError, OSError, ValueError) as exc:
            raise SystemExit(str(exc)) from exc

        for w in warnings:
            self.stdout.write(self.style.WARNING(w))

        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS("Dry run OK (no database changes)."))
            return

        self.stdout.write(
            self.style.SUCCESS(f"Squad import finished: {created} created, {updated} updated.")
        )

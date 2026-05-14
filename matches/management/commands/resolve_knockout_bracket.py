from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from matches.bracket import apply_knockout_feeds


class Command(BaseCommand):
    help = (
        "Apply KnockoutFeed rules: for each feed, set the target match home/away team to the "
        "winner of the source match if finished, otherwise to the predicted winner from the "
        "latest PredictionSnapshot when decisive."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Count updates that would occur without writing.",
        )

    def handle(self, *args, **options):
        dry: bool = options["dry_run"]
        if dry:
            updated, skipped = apply_knockout_feeds(dry_run=True)
        else:
            with transaction.atomic():
                updated, skipped = apply_knockout_feeds(dry_run=False)
        self.stdout.write(
            self.style.SUCCESS(
                f"Knockout resolution: updated={updated}, skipped (no decisive winner/prediction)={skipped}"
            )
        )

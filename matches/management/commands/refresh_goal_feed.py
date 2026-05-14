from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from matches.integrations.goal_com import fetch_goal_us_html, parse_headlines_from_home
from matches.models import NewsFeedItem


class Command(BaseCommand):
    help = (
        "Fetch Goal.com US home page and store headline links for the public home page. "
        "Markup changes can break parsing; respect robots.txt and site terms in production."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--limit",
            type=int,
            default=18,
            help="Max headlines to store (default 18).",
        )

    def handle(self, *args, **options):
        limit = max(1, min(int(options["limit"]), 40))
        html = fetch_goal_us_html()
        rows = parse_headlines_from_home(html, limit=limit)
        if not rows:
            self.stderr.write(self.style.WARNING("No headlines parsed; Goal.com layout may have changed."))
            return
        with transaction.atomic():
            NewsFeedItem.objects.all().delete()
            for title, url in rows:
                NewsFeedItem.objects.create(title=title, url=url, source="goal.com")
        self.stdout.write(self.style.SUCCESS(f"Stored {len(rows)} Goal.com US headlines."))

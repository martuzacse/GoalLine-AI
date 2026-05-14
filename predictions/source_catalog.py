"""
Reference catalog for stats, news, official, tactical, and historical sources.

Integration note: prefer licensed APIs, official feeds, and human-curated excerpts in
``Match.external_news_digest``. Automated scraping must respect each site's robots.txt
and terms of use; this module only documents intended provenance for curators and prompts.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceEntry:
    name: str
    url: str
    description: str = ""


@dataclass(frozen=True)
class SourceCategory:
    slug: str
    title: str
    entries: tuple[SourceEntry, ...]


SOURCE_CATEGORIES: tuple[SourceCategory, ...] = (
    SourceCategory(
        slug="stats",
        title="Stats & data",
        entries=(
            SourceEntry(
                "Transfermarkt",
                "https://www.transfermarkt.com",
                "Market values, transfers, contracts, squad pages across leagues.",
            ),
            SourceEntry(
                "FBref",
                "https://fbref.com",
                "Deep team/player stats including advanced metrics (e.g. xG, progressive actions).",
            ),
            SourceEntry(
                "WhoScored",
                "https://www.whoscored.com",
                "Match ratings, detailed event-style stats, tactical views.",
            ),
            SourceEntry(
                "SofaScore",
                "https://www.sofascore.com",
                "Live scores, lineups, heatmaps, player ratings across many competitions.",
            ),
            SourceEntry(
                "Opta / The Analyst",
                "https://theanalyst.com",
                "Data-led analysis from a major football stats provider.",
            ),
        ),
    ),
    SourceCategory(
        slug="news",
        title="News & coverage",
        entries=(
            SourceEntry(
                "BBC Sport Football",
                "https://www.bbc.com/sport/football",
                "News, scores, and fixtures with strong editorial standards.",
            ),
            SourceEntry(
                "ESPN FC",
                "https://www.espn.com/soccer",
                "Global coverage, news, and features.",
            ),
            SourceEntry(
                "The Guardian Football",
                "https://www.theguardian.com/football",
                "Long-form reporting and analysis.",
            ),
            SourceEntry(
                "Goal.com (US edition)",
                "https://www.goal.com/en-us",
                "News and features; optional `refresh_goal_feed` command caches headline links for the home page (best-effort HTML parsing).",
            ),
            SourceEntry(
                "The Athletic (football)",
                "https://theathletic.com/football",
                "In-depth journalism; subscription required for most articles.",
            ),
        ),
    ),
    SourceCategory(
        slug="official",
        title="Official sources",
        entries=(
            SourceEntry(
                "FIFA",
                "https://www.fifa.com",
                "Rankings, tournaments, and national-team competition information.",
            ),
            SourceEntry(
                "FIFA World Cup 2026 — schedule, fixtures & results",
                "https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/match-schedule-fixtures-results-teams-stadiums",
                "Official FIFA page for the Canada/Mexico/USA 2026 match schedule, stadiums, and results hub.",
            ),
            SourceEntry(
                "UEFA",
                "https://www.uefa.com",
                "European national and club competitions.",
            ),
            SourceEntry(
                "Premier League",
                "https://www.premierleague.com",
                "Official club and player pages for England's top tier.",
            ),
            SourceEntry(
                "La Liga",
                "https://www.laliga.com",
                "Official Spanish top-flight site.",
            ),
            SourceEntry(
                "Bundesliga",
                "https://www.bundesliga.com",
                "Official German league hub.",
            ),
            SourceEntry(
                "Serie A",
                "https://www.legaseriea.it",
                "Official Italian Serie A portal.",
            ),
            SourceEntry(
                "Ligue 1",
                "https://www.ligue1.com",
                "Official French top division.",
            ),
        ),
    ),
    SourceCategory(
        slug="tactical",
        title="Tactical & analytical",
        entries=(
            SourceEntry(
                "The Coaches' Voice",
                "https://www.coachesvoice.com",
                "Tactical breakdowns from coaches and analysts.",
            ),
            SourceEntry(
                "Tifo Football",
                "https://www.tifofootball.com",
                "Written explainers; companion video on YouTube under the Tifo Football channel.",
            ),
        ),
    ),
    SourceCategory(
        slug="historical",
        title="Historical / reference",
        entries=(
            SourceEntry(
                "RSSSF",
                "https://www.rsssf.org",
                "Extensive archive of results, records, and international football history.",
            ),
            SourceEntry(
                "Wikipedia",
                "https://en.wikipedia.org/wiki/Association_football",
                "Useful bios, timelines, and overview pages; verify against primary sources when possible.",
            ),
        ),
    ),
)


AGENT_SOURCE_POLICY = (
    "Human-curated digests in this app should, where possible, reflect: "
    "stats from Transfermarkt, FBref, WhoScored, SofaScore, or The Analyst; "
    "news from BBC Sport, ESPN FC, The Guardian, Goal, or The Athletic; "
    "official FIFA/UEFA or league releases for squad and competition facts; "
    "tactical context from The Coaches' Voice or Tifo; "
    "historical framing from RSSSF or Wikipedia when cited carefully. "
    "Player rows may include curator-provided recent club score strings, performance summaries, "
    "and structured stats snapshots—treat them as primary evidence for scorer and scoreline reasoning when present. "
    "Do not claim you browsed live websites unless concrete excerpts or URLs appear in the digest. "
    "When data is missing, lower confidence and say what is unknown."
)

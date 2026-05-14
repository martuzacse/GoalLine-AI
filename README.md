# Football World Cup Prediction (GoalLine-AI)

Django app for **curated match context**, **DeepSeek-powered scoreline forecasts**, and a **public UI** for rounds, fixtures, group tables, search, and light calibration insights. Data lives in your database (Postgres on Neon in production, SQLite locally if you omit `DATABASE_URL`).

Predictions are **experimental** and not betting advice.

## Features

- **Match pages**: prediction snapshot timeline, latest reasoning and factors, optional **prematch brief**, **JSON lineups**, **match events** (timeline), **snapshot diff** vs the previous snapshot, and optional **what-if** query params (`?what_home=2&what_away=1`).
- **Agent**: “Run DeepSeek agent” from a match page (requires API key). In `DEBUG` mode, a **stub** prediction avoids the API.
- **Fixtures hub**: World Cup vs current competitions tabs, filters, and search within the hub.
- **Global search** (`/search/`): teams, players, and matches.
- **Team & player** pages: squad lists, fixtures, and player narrative fields used by the agent.
- **World Cup groups** (`/wc/groups/`): **standings** derived from finished group matches in the DB plus a fixture list for that group letter.
- **Insights** (`/insights/`): coverage counts and a **calibration** table (goal error on latest snapshot vs final score).
- **Kickoff times**: stored in **UTC** in the database; the UI formats them in **each visitor’s browser time zone** (`static/js/local-time.js`).
- **World Cup knockout rounds**: optional placeholder fixtures for **Round of 32** through **Final** (plus **Third-place play-off**), loaded separately; **KnockoutFeed** in admin wires “winner of match X” into a later slot. `resolve_knockout_bracket` uses **final scores** when available, otherwise the **latest predicted scoreline** if decisive.
- **Home page**: **Today’s matches** (from your DB, local calendar day via `GET /api/today-matches/?tz=…`) and **Goal.com US** headline cache (`refresh_goal_feed`). **Official scores** should still be curated in admin (or a licensed API); automated HTML parsing of live scores is fragile and not implemented here.

## Requirements

- **Python 3.10+** recommended (Django 4.2 per `requirements.txt`).
- Dependencies are listed in `requirements.txt`.

## Local setup

1. Clone the repo and create a virtualenv.

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Copy environment template and adjust:

   ```bash
   cp env.example .env
   ```

   For local SQLite-only dev you can leave `DATABASE_URL` unset; for Postgres set `DATABASE_URL` as in `env.example`.

4. Migrate and run:

   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

5. Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) and [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/) (create a superuser with `python manage.py createsuperuser`).

Press **`/`** in the site (outside inputs) to focus the header search.

## Environment variables

Documented in **`env.example`**. Important entries:

| Variable | Purpose |
|----------|---------|
| `DEEPSEEK_API_KEY` | Required for live agent runs |
| `DEEPSEEK_API_BASE` / `DEEPSEEK_MODEL` | Optional overrides |
| `DJANGO_SECRET_KEY` | Required in production |
| `DATABASE_URL` | Postgres (e.g. Neon); omit for default SQLite |
| `DEBUG`, `ALLOWED_HOSTS` | Standard Django |
| `AUTO_SEED_DEMO`, `AUTO_LOAD_WC2026` | Control auto seed / WC fixture load on boot (see `env.example`) |

## Useful management commands

| Command | Purpose |
|---------|---------|
| `python manage.py migrate` | Apply schema |
| `python manage.py ensure_initial_data` | Idempotent demo / bootstrap (also referenced from `build.sh` / `start.sh`) |
| `python manage.py load_wc2026_fixtures --replace-wc` | Load 72 group-stage WC rows from `matches/wc2026_data.py` |
| `python manage.py load_wc2026_knockout` | Append 32 knockout placeholder matches (use `--force` to replace only those rounds) |
| `python manage.py resolve_knockout_bracket` | Apply `KnockoutFeed` rules (results or predictions) |
| `python manage.py refresh_goal_feed` | Fetch [Goal.com US](https://www.goal.com/en-us) and cache headline links (best-effort; respect ToS/robots) |
| `python manage.py import_squad_json --file matches/data/....json` | Import squads after editing JSON |
| `python manage.py seed_demo` | Demo data (see command help) |

## Production (e.g. Render)

- **Build**: `./build.sh` — installs deps, migrates, optional `ensure_initial_data`, `collectstatic`.
- **Start**: `./start.sh` — migrate, `ensure_initial_data`, optional `collectstatic`, then Gunicorn.

Neon / empty-schema notes, WhiteNoise, and CSRF hints are summarized in **`env.example`**.

### If the site returns 500 after deploy

1. **Run migrations** (includes `matches_newsfeeditem` / `knockoutfeed`): `python manage.py migrate --noinput`
2. **Reinstall deps** so `beautifulsoup4` is present (used only by `refresh_goal_feed`, not normal page loads).
3. Check **Render / host logs** for the traceback; the app now tolerates a missing `NewsFeedItem` table and a missing `matches_today_json` route when resolving the base layout URL.
4. If any **`round_name` in the database contains `/`**, older URL patterns broke every page’s header; the route now uses `<path:round_name>` so those names resolve. Redeploy after pulling the fix.

## Project layout (high level)

| Path | Role |
|------|------|
| `config/` | Django settings, WSGI, URLs |
| `matches/` | Teams, players, matches, events, WC data, standings helpers |
| `predictions/` | Snapshots, views, analysis helpers, agent integration |
| `templates/` | HTML templates |
| `static/` | CSS and static assets |

## Main URLs (all under site root)

| Path | Description |
|------|-------------|
| `/` | Home / rounds |
| `/api/today-matches/` | JSON: today’s matches for an IANA zone (`?tz=America/New_York`) |
| `/fixtures/` | Fixtures hub |
| `/search/` | Global search |
| `/wc/groups/` | Group index |
| `/wc/group/<A–L>/` | Standings + fixtures for that group |
| `/insights/` | Insights and calibration table |
| `/team/<code>/` | Team detail |
| `/player/<id>/` | Player detail |
| `/round/<round_name>/` | Round matches |
| `/match/<id>/` | Match detail and agent actions |
| `/sources/` | Reference source list |
| `/admin/` | Django admin |

## Curating richer match pages

In **admin → Matches**, you can set:

- **Prematch brief** (public narrative block).
- **Lineup home / away**: JSON list of strings (e.g. `"#9 Name"`) or small objects with `player` / `name`.
- **Match events** (inline): minute, type, side, headline, detail.

Re-run the agent after substantive edits so new **prediction snapshots** and **diffs** reflect your updates.

### Knockout bracket (optional)

1. Load placeholders: `python manage.py load_wc2026_knockout` (add `--force` to replace knockout-phase rows only).
2. In **admin → Matches**, open each advancing tie and add **Knockout bracket feeds** so a later match’s home or away side should receive the **winner** of an earlier match.
3. Run `python manage.py resolve_knockout_bracket` after results or predictions change (e.g. on a cron every 15 minutes during the tournament).

### Goal.com US headlines (optional)

Run `python manage.py refresh_goal_feed` on a schedule so the home page “Match updates” list stays fresh. Parsing is heuristic; review [Goal.com](https://www.goal.com/en-us) terms and robots.txt for your deployment. **Scores** in this app are driven by your database (admin or your own data pipeline), not by live scraping of Goal scoreboards.

# course-search-bot

Discord course search for Taiwanese universities. One schema, one adapter per school.

## Run

```sh
uv sync
uv run pytest -q                       # 56 tests
uv run pytest -q -m "not integration"  # 54, no network
uv run ruff check . && uv run ruff format --check .
DISCORD_TOKEN=... uv run bot.py        # /course 微積分
```

Only tests marked `integration` hit a live university feed, and they skip rather
than fail when offline. Everything else runs against `tests/data/nthu_sample.json`
— ten real records, each kept for a quirk it carries.

Runs on fixtures until an adapter lands. No scraper needed to develop the bot.

## Layout

| File | Owner | School-specific? |
|---|---|---|
| `schema.py` | this repo | no — the contract |
| `search.py` | this repo | no |
| `bot.py` | this repo | no |
| `conformance.py` | this repo | no — the contract check |
| `adapters/*.py` | contributors | **yes** — the only bespoke part |

## Data sources

| School | Source | Login? | Notes |
|---|---|---|---|
| NTHU | [`open_course_data.json`](https://www.ccxp.nthu.edu.tw/ccxp/INQUIRE/JH/OPENDATA/open_course_data.json) | no | official, daily, ~3.4 MB, current semester only |
| NCKU | `course-query.acad.ncku.edu.tw` | no | not written yet |

Neither adapter touches a logged-in page. Enrollment counts are not published in
NTHU's feed, so `enrolled` is None; seat tracking would need a captcha-gated
endpoint and is deliberately out of scope.

## Adding a school

1. Copy `adapters/nthu.py`, implement `semesters()` and `courses(semester)`
2. Return `Course` objects — public catalog data only, never logged-in pages
3. Pass `conforms()` in `tests/test_conformance.py`

Meaning is encoded differently at every school (NTHU: character offsets in the
course id; NCKU: CSS colors and `display:none`; NTUT: plain tables). The adapter
absorbs that so nothing downstream has to know.

## Hosting note

`discord.py` uses the gateway, so it needs an always-on process. `search.py`,
`schema.py`, and the adapters have no Discord dependency, so switching to HTTP
interactions (serverless, $0) later means rewriting `bot.py` only.

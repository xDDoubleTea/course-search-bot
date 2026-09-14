# course-search-bot

**English** · [繁體中文](README.zh-TW.md)

Discord course search for Taiwanese universities. One schema, one adapter per school.

## How this was built

Almost all of the code, tests and documentation here were written by
[Claude Code](https://claude.com/claude-code). The design decisions, the review
and the final call on every change are the author's — nothing is merged without
being read and understood first — but you should assume the prose and the
implementation are model-generated.

This matters most for the adapters. Each one was validated against the live
source before being committed (every `時間` string parsed, every `cos_time`
grammar checked), and the integration tests re-check that on demand. Trust the
tests, not the confident tone.

## Run

```sh
uv sync
uv run pytest -q                       # 103 tests
uv run pytest -q -m "not integration"  # 96, no network
uv run ruff check . && uv run ruff format --check .
DISCORD_TOKEN=... uv run bot.py        # /course 微積分
```

Only tests marked `integration` reach a live university source, and they skip
rather than fail when offline. Everything else runs against frozen samples in
`tests/data/`, each record kept for a quirk it carries.

## Layout

| File | Owner | School-specific? |
|---|---|---|
| `schema.py` | this repo | no — the contract |
| `search.py` | this repo | no |
| `bot.py` | this repo | no |
| `conformance.py` | this repo | no — the contract check |
| `adapters/*.py` | contributors | **yes** — the only bespoke part |

## Data sources

| School | Source | Login | Shape |
|---|---|---|---|
| NTHU | [`open_course_data.json`](https://www.ccxp.nthu.edu.tw/ccxp/INQUIRE/JH/OPENDATA/open_course_data.json) | none | official, daily, ~3.4 MB, one request |
| NYCU | [`timetable.nycu.edu.tw`](https://timetable.nycu.edu.tw/) | none | `?r=main/*` JSON, one request per department (~257) |
| NCKU | [`nckuhub.com`](https://nckuhub.com/course/) | none | third-party mirror, one request |

No adapter touches a logged-in page, solves a captcha, or uses a proxy pool.
An adapter that needs any of those does not belong here.

NCKU's own catalogue is not usable: every filter value is a per-session
encrypted token, the query JavaScript is obfuscated, and a captcha gate fires
under load. NCKU HUB scrapes it server-side and republishes public JSON.

Enrolment counts are not exposed for any school. NTHU does not publish them,
NYCU returns `-999` outside the enrolment window, and NCKU HUB's figures carry
mixed ages. `capacity` and `enrolled` are `None` rather than misleading.

## Adding a school

1. Copy `adapters/nthu.py`, implement `semesters()` and `courses(semester)`
2. Return `Course` objects — public catalogue data only, never logged-in pages
3. Pass `conforms()` from `conformance.py`

Every school encodes meaning somewhere different: NTHU in character offsets
within the course id, NYCU in a packed `cos_time` string, NCKU in a bracketed
day-period grammar with HTML spliced into the field. The adapter absorbs that
so nothing downstream has to know.

## Data and conduct

The code is MIT-licensed. **The course data is not ours.** It belongs to the
universities, and in NCKU's case to NCKU HUB, a volunteer project that is not
affiliated with the university.

If you run or fork this:

- Read only public endpoints. Never authenticate as a student.
- Crawl on a schedule, not per user query. A full NYCU crawl is ~257 requests;
  run it once a day, not once a search.
- Cache. These are small university servers, not a CDN.
- Do not redistribute bulk course data as if it were yours.

## Hosting note

`discord.py` uses the gateway, so it needs an always-on process. `schema.py`,
`search.py`, and the adapters have no Discord dependency, so moving to HTTP
interactions (serverless) later means rewriting `bot.py` only.

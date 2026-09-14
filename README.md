# course-search-bot

Discord course search for Taiwanese universities. One schema, one adapter per school.

## Run

```sh
uv sync
uv run pytest -q                   # 7 passing
DISCORD_TOKEN=... uv run bot.py    # /course 微積分
```

Runs on fixtures until an adapter lands. No scraper needed to develop the bot.

## Layout

| File | Owner | School-specific? |
|---|---|---|
| `schema.py` | this repo | no — the contract |
| `search.py` | this repo | no |
| `bot.py` | this repo | no |
| `tests/test_conformance.py` | this repo | no |
| `adapters/*.py` | contributors | **yes** — the only bespoke part |

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

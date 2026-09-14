# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```sh
uv sync
uv run pytest -q                          # everything, including live sources
uv run pytest -q -m "not integration"     # offline, fast; use this by default
uv run pytest -q tests/test_ncku.py       # one file
uv run pytest -q -k noon                  # one test by name
uv run pytest --cov --cov-report=term-missing -m "not integration"
uv run ruff check . && uv run ruff format --check .
DISCORD_TOKEN=... uv run bot.py
```

Tests marked `integration` reach live university sources. They skip rather than
fail when offline, and they are the only tests that touch the network.

## Architecture

The design constraint behind everything: this must run with **no always-on
infrastructure and no privileged access**. Every project that tried to be a
course *enrolment* system in Taiwan died when its author graduated and the
server bill stopped being paid. So nothing here authenticates as a student,
solves a captcha, or uses a proxy pool, and an adapter that needs any of those
does not belong in the repo.

`schema.Course` is the contract. Everything except `adapters/` is school-agnostic
and depends only on it:

```
adapters/*.py  ->  Course  ->  search.py / catalog.py  ->  bot.py
   bespoke        contract         generic              Discord only
```

Adding a school means writing one adapter and registering it in
`catalog.ADAPTERS`. Nothing downstream changes.

`conformance.conforms()` is the contract check, deliberately kept out of `tests/`
so an adapter in another repo can import it.

### Crawl, then search locally

A full crawl is slow (NYCU is ~257 requests, about three minutes). `catalog.py`
fetches on a schedule, caches JSON under `.cache/`, and search runs in memory.
**Never fetch inside a command handler** — Discord gives you three seconds, and a
global keyword query against NYCU alone takes five.

A school that fails to load is skipped, not fatal. These are unattended
university servers.

### Ranking

`search.py` uses `rapidfuzz.partial_ratio`, which scores *every* superstring 100.
A common query therefore ties hundreds of courses, so all candidates above the
cutoff are kept (`limit=None`) and ordered afterwards: exact title, then score,
then shortest title. Truncating in `process.extract` silently drops exact
matches — that was a real bug, and `test_exact_title_outranks_longer_matches`
guards it.

`fold()` is applied to the data as well as the query. The feeds themselves
contain fullwidth characters, so folding only user input still misses.

## Working on adapters

Every school encodes meaning somewhere different, and each of these was found by
validating against live data, not by reading documentation:

- **NTHU** — `科號` is fixed-width; position 8 is not always a space. Periods run
  `1-9 n a b c d`. The feed claims UTF-16 but is ASCII with `\uXXXX` escapes, and
  carries raw HTML entities. The certificate omits the Subject Key Identifier, so
  every adapter builds an `ssl` context with `VERIFY_X509_STRICT` cleared.
- **NYCU** — unset query parameters must be the string `"**"`; `""` returns a bare
  400. Academic years are two *or* three digits (`99X` and `1151` both exist).
  `cos_time` can be comma-separated, where one slot in two rooms is one class.
- **NCKU** — read via `nckuhub.com`, not the university; NCKU's own catalogue uses
  per-session encrypted filter values and a captcha. `N` is the noon period,
  ordered *between* 4 and 5. Raw HTML is spliced into the `時間` field. The live
  list has no semester label, so the current term is derived from the archive,
  which lags one term.

Weekday letters (`M T W R F S U`) are shared across schools even where the source
numbers them, so `Course.times` is normalised rather than the school's notation.

Seat counts are deliberately `None` everywhere. No school publishes reliable
current enrolment, and a wrong seat count is worse than no seat count.

**Validate a parser against the whole live feed before committing it** — count
the inputs that parse to nothing. Every adapter bug found so far was a format the
documentation did not mention.

## Conventions

- Conventional commits; squash merge via PR.
- Fixtures in `tests/data/` are real records, each kept for a specific quirk.
  When adding one, note in the test which quirk it covers.

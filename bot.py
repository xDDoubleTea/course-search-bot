"""discord.py entrypoint.

Nothing below the Discord layer knows Discord exists: schema, search, catalog
and the adapters are all importable without it. Moving to HTTP interactions
later means rewriting this file and nothing else.
"""

import logging
import os

import discord
from discord import app_commands

import catalog
from schema import Course
from search import build_index, search

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("bot")

MAX_RESULTS = 5

COURSES: list[Course] = []
INDEX: list[str] = []

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


def reload_catalog(refresh: bool = False) -> None:
    global COURSES, INDEX
    COURSES = catalog.load(refresh=refresh)
    INDEX = build_index(COURSES)
    by_school = {s: sum(1 for c in COURSES if c.school == s) for s in catalog.ADAPTERS}
    logger.info("catalog: %d courses %s", len(COURSES), by_school)


def embed_for(c: Course) -> discord.Embed:
    embed = discord.Embed(
        title=" · ".join(filter(None, (c.name_zh, c.name_en))),
        description=f"`{c.id}` — {c.school.upper()} {c.semester}",
    )
    embed.add_field(name="教師", value="、".join(c.teachers) or "—")
    embed.add_field(name="時間", value=" ".join(c.times) or "—")
    embed.add_field(name="地點", value=" ".join(c.venues) or "—")
    embed.add_field(name="學分", value=f"{c.credits:g}")
    embed.add_field(name="系所", value=c.department or "—")
    if c.seats_left is not None:
        embed.add_field(name="餘額", value=f"{c.seats_left} / {c.capacity}")
    return embed


@tree.command(name="course", description="Search for a course")
@app_commands.describe(query="Course name, teacher, or department")
@app_commands.choices(
    school=[
        app_commands.Choice(name=s.upper(), value=s) for s in sorted(catalog.ADAPTERS)
    ]
)
async def course(
    interaction: discord.Interaction,
    query: str,
    school: app_commands.Choice[str] | None = None,
):
    if school is None:
        hits = search(COURSES, query, limit=MAX_RESULTS, index=INDEX)
    else:
        pool = [c for c in COURSES if c.school == school.value]
        hits = search(pool, query, limit=MAX_RESULTS)
    if not hits:
        await interaction.response.send_message(
            f"No match for `{query}`.", ephemeral=True
        )
        return
    await interaction.response.send_message(embeds=[embed_for(c) for c in hits])


@client.event
async def on_ready():
    await tree.sync()
    logger.info("ready as %s", client.user)


def main() -> None:
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise SystemExit("set DISCORD_TOKEN")
    reload_catalog()
    if not COURSES:
        raise SystemExit("no school loaded; refusing to start with an empty catalog")
    client.run(token)


if __name__ == "__main__":
    main()

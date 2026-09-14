"""discord.py entrypoint. Swappable: search.py and schema.py know nothing about Discord,
so moving to HTTP interactions later means replacing only this file."""

import os
import discord
from discord import app_commands

from schema import Course
from search import search
from tests.fixtures import FIXTURES

SCHOOLS = ["nthu", "ncku"]


def load_courses() -> list[Course]:
    """Swap for a fetch of the published static JSON once adapters exist."""
    return FIXTURES


COURSES = load_courses()

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


def embed_for(c: Course) -> discord.Embed:
    e = discord.Embed(
        title=f"{c.name_zh} · {c.name_en}",
        description=f"`{c.id}` — {c.school.upper()} {c.semester}",
    )
    e.add_field(name="教師", value="、".join(c.teachers) or "—")
    e.add_field(name="時間", value=" ".join(c.times) or "—")
    e.add_field(name="地點", value=" ".join(c.venues) or "—")
    e.add_field(name="學分", value=str(c.credits))
    left = c.seats_left
    if left is not None:
        e.add_field(name="餘額", value=f"{left} / {c.capacity}")
    return e


@tree.command(name="course", description="Search for a course")
@app_commands.describe(query="Course name, teacher, or department")
@app_commands.choices(school=[app_commands.Choice(name=s.upper(), value=s) for s in SCHOOLS])
async def course(
    interaction: discord.Interaction,
    query: str,
    school: app_commands.Choice[str] | None = None,
):
    pool = COURSES if school is None else [c for c in COURSES if c.school == school.value]
    hits = search(pool, query, limit=5)
    if not hits:
        await interaction.response.send_message(f"No match for `{query}`.", ephemeral=True)
        return
    await interaction.response.send_message(embeds=[embed_for(c) for c in hits])


@client.event
async def on_ready():
    await tree.sync()
    print(f"ready as {client.user} — {len(COURSES)} courses loaded")


if __name__ == "__main__":
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise SystemExit("set DISCORD_TOKEN")
    client.run(token)

"""Mig's World GTA VI countdown bot.

Keeps one persistent Discord message updated without privileged gateway intents.
"""

import json
import logging
import math
import os
from datetime import datetime, timezone
from pathlib import Path

import discord
from discord.ext import tasks
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("migs-countdown")

EVENT_URL = "https://discord.gg/rSUVaYmUa?event=1569361550597169286"
COUNTDOWN_URL = "https://migtam628.github.io/gta-vi/"
EVENT_TITLE = "🌴 GTA VI — THE FINAL COUNTDOWN"
FOOTER = "Mig's World • Unofficial GTA VI fan event"


def required_int(name: str) -> int:
    value = os.environ.get(name, "").strip()
    if not value.isdecimal() or int(value) < 1:
        raise SystemExit(f"Set {name} to a valid positive Discord ID in your .env file")
    return int(value)


TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()
if not TOKEN:
    raise SystemExit("DISCORD_BOT_TOKEN is missing. Set it in .env; never commit the token.")
CHANNEL_ID = required_int("DISCORD_CHANNEL_ID")
TARGET = datetime.fromisoformat(os.getenv("KICKOFF_UTC", "2026-11-19T04:45:00+00:00"))
if TARGET.tzinfo is None:
    raise SystemExit("KICKOFF_UTC must include a UTC offset")
TARGET = TARGET.astimezone(timezone.utc)
TARGET_TS = int(TARGET.timestamp())
START = datetime(2026, 11, 9, tzinfo=timezone.utc)
UPDATE_SECONDS = max(15, int(os.getenv("UPDATE_INTERVAL_SECONDS", "15")))
PIN_MESSAGE = os.getenv("PIN_MESSAGE", "false").lower() in ("1", "true", "yes")
STATE_PATH = Path(os.getenv("STATE_FILE", "/data/message.json"))

intents = discord.Intents.none()
intents.guilds = True
client = discord.Client(intents=intents, allowed_mentions=discord.AllowedMentions.none())
message: discord.Message | None = None
last_second: int | None = None


def view() -> discord.ui.View:
    buttons = discord.ui.View(timeout=None)
    buttons.add_item(discord.ui.Button(label="Join Discord Event", emoji="🎮", style=discord.ButtonStyle.link, url=EVENT_URL))
    buttons.add_item(discord.ui.Button(label="Open Live Countdown", emoji="🌐", style=discord.ButtonStyle.link, url=COUNTDOWN_URL))
    return buttons


def remaining_seconds(now: datetime) -> int:
    return max(0, math.ceil((TARGET - now).total_seconds()))


def make_embed(now: datetime) -> discord.Embed:
    total_seconds = remaining_seconds(now)
    days, extra = divmod(total_seconds, 86400)
    hours, extra = divmod(extra, 3600)
    mins, seconds = divmod(extra, 60)
    if now >= TARGET:
        description = "## 🎉 THE PARTY IS LIVE!\nWelcome to Vice City! Join us in Mig's World."
        color = discord.Color.from_rgb(72, 232, 252)
    else:
        description = (
            f"## ⏳ {days:02d} DAYS · {hours:02d} HOURS · {mins:02d} MIN · {seconds:02d} SEC\n"
            f"**Kickoff <t:{TARGET_TS}:R>** — this Discord timestamp updates automatically.\n\n"
            "🌴 Vice City hype • 🎙️ Community voice chat • 🏆 GTA trivia"
        )
        color = discord.Color.from_rgb(255, 59, 186)
    embed = discord.Embed(title=EVENT_TITLE, description=description, color=color)
    embed.add_field(name="📅 Launch Eve Party", value=f"<t:{TARGET_TS}:F>", inline=False)
    embed.add_field(name="🎮 Join the crew", value="Use the event button below to RSVP or join the party.", inline=False)
    embed.set_footer(text=FOOTER + f" • Updates about every {UPDATE_SECONDS}s • Not a game unlock timer")
    return embed


def load_id() -> int | None:
    override = os.getenv("DISCORD_MESSAGE_ID", "").strip()
    if override.isdecimal():
        return int(override)
    try:
        value = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        if int(value.get("channel_id", 0)) == CHANNEL_ID:
            return int(value["message_id"])
    except (FileNotFoundError, OSError, ValueError, KeyError, TypeError):
        pass
    return None


def save_id(message_id: int) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps({"channel_id": CHANNEL_ID, "message_id": message_id}), encoding="utf-8")
    tmp.replace(STATE_PATH)


async def get_channel():
    channel = client.get_channel(CHANNEL_ID) or await client.fetch_channel(CHANNEL_ID)
    if not hasattr(channel, "send") or not hasattr(channel, "fetch_message"):
        raise RuntimeError("DISCORD_CHANNEL_ID must be a regular Discord text channel")
    return channel


async def locate_existing(channel):
    existing_id = load_id()
    if existing_id:
        try:
            return await channel.fetch_message(existing_id)
        except discord.NotFound:
            logger.warning("Saved countdown message was deleted; checking recent channel history")
    # Recover safely if the volume was recreated: prefer to edit the old bot message.
    async for candidate in channel.history(limit=75):
        if (client.user and candidate.author.id == client.user.id and candidate.embeds
                and candidate.embeds[0].title == EVENT_TITLE):
            return candidate
    return None


async def publish() -> None:
    global message, last_second
    now = datetime.now(timezone.utc)
    seconds = remaining_seconds(now)
    if message is not None and last_second == seconds:
        return
    channel = message.channel if message is not None else await get_channel()
    if message is None:
        message = await locate_existing(channel)
    card = make_embed(now)
    buttons = view()
    if message is None:
        message = await channel.send(embed=card, view=buttons, silent=True)
        save_id(message.id)
        logger.info("Created countdown message: %s", message.jump_url)
        if PIN_MESSAGE:
            try:
                await message.pin(reason="Mig's World GTA VI countdown")
            except discord.Forbidden:
                logger.warning("PIN_MESSAGE enabled but bot lacks Manage Messages permission")
    else:
        try:
            message = await message.edit(embed=card, view=buttons)
        except discord.NotFound:
            logger.warning("Countdown message was removed; creating one replacement")
            message = await channel.send(embed=card, view=buttons, silent=True)
            save_id(message.id)
        logger.info("Updated countdown message %s: %s seconds remain", message.id, seconds)
    last_second = seconds


@tasks.loop(seconds=15, reconnect=True)
async def update_countdown() -> None:
    try:
        await publish()
    except (discord.Forbidden, discord.HTTPException, OSError, RuntimeError):
        logger.exception("Countdown update failed; retrying on next interval")


@update_countdown.before_loop
async def wait_ready() -> None:
    await client.wait_until_ready()


@client.event
async def on_ready() -> None:
    logger.info("Connected as %s; target channel %s", client.user, CHANNEL_ID)
    if not update_countdown.is_running():
        update_countdown.change_interval(seconds=UPDATE_SECONDS)
        update_countdown.start()


if __name__ == "__main__":
    client.run(TOKEN, log_handler=None)

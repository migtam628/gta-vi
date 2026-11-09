"""Mig's World bilingual Discord scheduled-post worker.

The worker posts *only* preapproved, dated posts from auto_post_schedule.json.
It never generates text dynamically, sends @everyone, or touches the countdown.
"""

import argparse
import hashlib
import json
import logging
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()
HERE = Path(__file__).resolve().parent
SCHEDULE_PATH = HERE / "auto_post_schedule.json"
STATE_PATH = Path(os.getenv("AUTO_POST_STATE_FILE", "/data/auto_post_state.json"))
API = "https://discord.com/api/v10"
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()
ENABLED = os.getenv("AUTO_POST_ENABLED", "true").strip().lower() in ("true", "1", "yes")
CHECK_SECONDS = max(60, int(os.getenv("AUTO_POST_CHECK_SECONDS", "60")))
GRACE_MINUTES = min(240, max(1, int(os.getenv("AUTO_POST_GRACE_MINUTES", "120"))))
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s scheduler: %(message)s")
log = logging.getLogger("migs-scheduled-posts")


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def write_state(data):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp = STATE_PATH.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    temp.replace(STATE_PATH)


def request(method, route, payload=None):
    if not BOT_TOKEN:
        raise RuntimeError("DISCORD_BOT_TOKEN is missing from the private environment")
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req_headers = {
        "Authorization": "Bot " + BOT_TOKEN,
        "User-Agent": "MigsWorldScheduledPosts/1.0",
        "Content-Type": "application/json",
    }
    for attempt in range(4):
        req = urllib.request.Request(API + route, data=body, headers=req_headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                data = response.read()
                return json.loads(data.decode("utf-8")) if data else {}
        except urllib.error.HTTPError as err:
            details = err.read().decode("utf-8")[:350]
            if err.code == 429 and attempt < 3:
                try:
                    delay = min(30, max(1, float(json.loads(details).get("retry_after", 3))))
                except (ValueError, TypeError, KeyError):
                    delay = 3
                log.warning("Rate limited; will retry in %s seconds", delay)
                time.sleep(delay)
                continue
            raise RuntimeError(f"Discord API {err.code}: {details}") from None
    raise RuntimeError("Discord API retry attempts exhausted")


def content(entry):
    return ("🇺🇸 **ENGLISH**\n" + entry["en"] +
            "\n\n━━━━━━━━━━━━━━━━\n\n" +
            "🇪🇸 **ESPAÑOL**\n" + entry["es"] +
            "\n\n*Mig's World • Unofficial fan community / Comunidad no oficial de fans*")


def load_schedule():
    schedule = read_json(SCHEDULE_PATH)
    if not schedule or str(schedule.get("guild_id")) != "866125624656789514":
        raise RuntimeError("Schedule is missing or not configured for Mig's World")
    tz = ZoneInfo(schedule["timezone"])
    entries = schedule["entries"]
    seen = set()
    for entry in entries:
        key = entry["id"]
        if key in seen:
            raise RuntimeError(f"Duplicate schedule ID: {key}")
        seen.add(key)
        when = datetime.fromisoformat(entry["at"])
        if when.tzinfo is None or when.astimezone(tz).utcoffset() != when.utcoffset():
            raise RuntimeError(f"Invalid Eastern-time timestamp for {key}")
        if len(content(entry)) > 2000:
            raise RuntimeError(f"Discord message would exceed 2,000 characters: {key}")
        if any(ping in content(entry).lower() for ping in ("@everyone", "@here")):
            raise RuntimeError(f"Mass mentions are forbidden in scheduled content: {key}")
    return schedule


def channels_for(guild_id):
    channels = request("GET", f"/guilds/{guild_id}/channels")
    result = {}
    for channel in channels:
        if channel.get("type") in (0, 5, 15, 16):
            result.setdefault(channel["name"], []).append(channel)
    return result


def send_post(guild_id, entry, channels):
    matching = channels.get(entry["channel"], [])
    if len(matching) != 1:
        raise RuntimeError(f"#{entry['channel']} missing or duplicated in Mig's World")
    channel = matching[0]
    channel_id = channel["id"]
    nonce = hashlib.sha256((str(guild_id) + ":" + entry["id"]).encode()).hexdigest()[:22]
    body = {"content": content(entry), "allowed_mentions": {"parse": []},
            "nonce": nonce, "enforce_nonce": True}
    if channel["type"] in (15, 16):
        # Forum or Media: write a post (thread), never post directly to its parent.
        if int(channel.get("flags") or 0) & 16:
            raise RuntimeError(f"#{entry['channel']} requires a tag; configure before auto-posting")
        thread = request("POST", f"/channels/{channel_id}/threads", {
            "name": entry.get("title", "GTA VI | Mig's World"),
            "auto_archive_duration": 1440,
            "message": body,
        })
        record_id = thread["id"]
        link = f"https://discord.com/channels/{guild_id}/{record_id}"
    else:
        response = request("POST", f"/channels/{channel_id}/messages", body)
        record_id = response["id"]
        link = f"https://discord.com/channels/{guild_id}/{channel_id}/{record_id}"
    return record_id, link


def run_due(schedule, now):
    state = read_json(STATE_PATH, default={})
    guild_id = str(schedule["guild_id"])
    due = []
    for entry in schedule["entries"]:
        when = datetime.fromisoformat(entry["at"]).astimezone(timezone.utc)
        elapsed = (now - when).total_seconds()
        allowed_age = min(GRACE_MINUTES, int(entry.get("grace_minutes", GRACE_MINUTES))) * 60
        if 0 <= elapsed <= allowed_age and entry["id"] not in state:
            due.append(entry)
    if not due:
        return
    try:
        channels = channels_for(guild_id)
    except RuntimeError as err:
        log.error("Cannot inspect channels: %s", err)
        return
    for entry in sorted(due, key=lambda v: v["at"]):
        try:
            record_id, url = send_post(guild_id, entry, channels)
        except RuntimeError as err:
            log.error("Failed to publish #%s (%s): %s", entry["channel"], entry["id"], err)
            continue
        state[entry["id"]] = {"message_id": str(record_id), "posted_utc": now.isoformat()}
        write_state(state)
        log.info("POSTED #%s — %s", entry["channel"], url)
        time.sleep(2)


def preview(schedule):
    tz = ZoneInfo(schedule["timezone"])
    now = datetime.now(timezone.utc)
    state = read_json(STATE_PATH, default={})
    print("Mig's World / Publicaciones bilingües")
    print("Auto-post enabled in environment:", ENABLED)
    print("Schedule timezone:", schedule["timezone"])
    print("Already posted:", len(state))
    for entry in schedule["entries"]:
        when = datetime.fromisoformat(entry["at"])
        past = when.astimezone(timezone.utc) < now
        status = "POSTED" if entry["id"] in state else ("MISSED/PAST" if past else "UPCOMING")
        print(f"{when.astimezone(tz):%Y-%m-%d %I:%M %p} ET | "
              f"#{entry['channel']:<20} | {entry['id']:<24} | {status}")


def main():
    parser = argparse.ArgumentParser(description="Mig's World bilingual scheduled posts")
    parser.add_argument("--preview", action="store_true",
                        help="Display schedule and state without sending anything")
    parser.add_argument("--run", action="store_true",
                        help="Keep running and publish approved entries at their scheduled times")
    args = parser.parse_args()
    schedule = load_schedule()
    if args.preview or not args.run:
        preview(schedule)
        return
    log.info("Started; enabled=%s; timezone=%s; planned_posts=%s",
             ENABLED, schedule["timezone"], len(schedule["entries"]))
    while True:
        if ENABLED:
            run_due(schedule, datetime.now(timezone.utc))
        time.sleep(CHECK_SECONDS)


if __name__ == "__main__":
    main()

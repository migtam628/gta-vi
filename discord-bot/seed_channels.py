"""Post the reviewed GTA VI starter pack to Mig's World Discord, once only.

Preview is the default. Publishing requires --publish and uses the bot token
already stored privately in the existing Docker Compose environment.
"""

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
HERE = Path(__file__).resolve().parent
PACK_PATH = HERE / "channel_seed_posts.json"
STATE_PATH = Path(os.environ.get("SEED_POST_STATE_FILE", "/data/channel_seed_state.json"))
API = "https://discord.com/api/v10"


def read_json(path: Path, fallback=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return fallback


def persist_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp = STATE_PATH.with_suffix(".tmp")
    temp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    temp.replace(STATE_PATH)


def discord_request(token, method, path, payload=None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": "Bot " + token,
        "User-Agent": "MigsWorldCountdownContent/1.0",
        "Content-Type": "application/json",
    }
    for retry in range(4):
        req = urllib.request.Request(
            API + path, headers=headers, data=body, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                result = response.read().decode("utf-8")
                return json.loads(result) if result else {}
        except urllib.error.HTTPError as err:
            detail = err.read().decode("utf-8")[:400]
            if err.code == 429 and retry < 3:
                try:
                    delay = min(20, max(1, float(json.loads(detail)["retry_after"])))
                except (ValueError, KeyError, TypeError):
                    delay = 3
                print(f"Discord rate-limited the request; retrying in {delay}s.")
                time.sleep(delay)
                continue
            raise RuntimeError(f"Discord API {err.code}: {detail}") from None
    raise RuntimeError("Discord API did not succeed after retries")


def main():
    parser = argparse.ArgumentParser(
        description="Preview or publish one starter post per GTA VI Discord channel")
    parser.add_argument("--publish", action="store_true",
                        help="Actually send Discord posts (otherwise preview only)")
    parser.add_argument("--only", action="append", default=[],
                        help="Channel name to publish/preview, repeatable")
    args = parser.parse_args()

    pack = read_json(PACK_PATH)
    if not pack or not pack.get("posts"):
        raise SystemExit("Missing starter posts")
    posts = [p for p in pack["posts"]
             if not args.only or p["channel"] in args.only]
    if args.only and len(set(args.only) - {p["channel"] for p in posts}):
        raise SystemExit("Unknown --only channel: " + ", ".join(
            sorted(set(args.only) - {p["channel"] for p in posts})))
    for post in posts:
        if len(post["content"]) > 2000:
            raise SystemExit(f"Discord 2000-char limit exceeded: {post['id']}")

    if not args.publish:
        print("PREVIEW ONLY — nothing will be posted.")
        for post in posts:
            print("\n" + "=" * 60)
            print(f"#{post['channel']} | {post['id']}")
            print(post["content"])
        print("\nTo send these messages, add --publish.")
        return

    token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit("DISCORD_BOT_TOKEN missing from private environment")
    guild = str(pack["server_id"])
    channels = discord_request(token, "GET", f"/guilds/{guild}/channels")
    by_name = {}
    for channel in channels:
        if channel.get("type") in (0, 5):
            by_name.setdefault(channel["name"], []).append(channel["id"])

    # Check all selected channel names before sending anything.
    problems = [p["channel"] for p in posts
                if len(by_name.get(p["channel"], [])) != 1]
    if problems:
        raise SystemExit("Channel missing or ambiguous (nothing sent): " +
                         ", ".join(problems) +
                         ". Check the bot's View Channel access and exact names.")

    state = read_json(STATE_PATH, fallback={})
    for post in posts:
        key = str(guild) + ":" + post["id"]
        if key in state:
            print(f"SKIP #{post['channel']}: already posted as {state[key]}")
            continue
        channel_id = by_name[post["channel"]][0]
        message = discord_request(token, "POST", f"/channels/{channel_id}/messages", {
            "content": post["content"],
            "allowed_mentions": {"parse": []},
        })
        message_id = message["id"]
        state[key] = message_id
        persist_state(state)
        print(f"POSTED #{post['channel']}: https://discord.com/channels/{guild}/{channel_id}/{message_id}")
        time.sleep(1)
    print("Done. Your live countdown message in #launch-countdown was not changed.")


if __name__ == "__main__":
    main()

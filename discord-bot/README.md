# Mig's World — GTA VI Discord Countdown Bot

One live-updating Discord **embed message** for the GTA VI community launch-eve party. The bot shows **days, hours, minutes, and seconds** and edits the **same message about every 15 seconds** by default (without sending new messages). Discord embed text cannot animate every second; use the live countdown website for a smooth 1-second timer. A native Discord relative timestamp stays up to date between edits. It includes link buttons for the [Discord event](https://discord.gg/rSUVaYmUa?event=1569361550597169286) and the [live countdown website](https://migtam628.github.io/gta-vi/).

**Kickoff:** Wednesday, November 18, 2026 at **11:45 PM America/New_York** (November 19 at 04:45 UTC). This is a fan party kickoff, not a guaranteed game unlock time.

## 1. Register and invite the bot

1. Open [Discord Developer Portal](https://discord.com/developers/applications) and click **New Application**, for example `Mig's World Countdown`.
2. On **Bot**, reveal/reset the **Bot Token** and **keep it secret**. Do not paste the token into Discord or ChatGPT.
3. On **Installation** (or OAuth2 URL Generator), enable **Guild Install** with `bot` scope. The `applications.commands` scope is optional; this bot doesn't need slash commands.
4. Grant **View Channel**, **Send Messages**, **Embed Links**, and **Read Message History**. If you want the bot to pin its own message (`PIN_MESSAGE=true`), additionally grant **Manage Messages**. Do **not** grant Administrator.
5. Use the generated install/invite link to add the bot to **Mig's World**.
6. Create a text channel such as `#gta6-countdown`. In Discord Settings > Advanced, enable **Developer Mode**, then right-click the channel > **Copy Channel ID**. Make sure the bot can view and send messages in that channel.

## 2. Deploy on an always-on Linux server using Docker

Run on the machine that will host the bot:

```bash
git clone https://github.com/migtam628/gta-vi.git
cd gta-vi/discord-bot
cp .env.example .env
nano .env
```

Replace `DISCORD_BOT_TOKEN` with the token and `DISCORD_CHANNEL_ID` with the numeric channel ID. Do not leave the placeholder values. **Never commit `.env` or your bot token**.

```bash
docker compose up -d --build
docker compose logs --tail=60 -f
```

The bot posts a single countdown and edits it approximately every 15 seconds (configurable with `UPDATE_INTERVAL_SECONDS`, minimum 15). It saves the message ID in a Docker named volume so restarts don't create duplicate announcements. If the state volume is lost, it checks recent channel history for the previous countdown. Optional `PIN_MESSAGE=true` pins the message if the bot has permission.

## Operations

```bash
docker compose ps
docker compose logs --tail=100
docker compose restart
docker compose down    # preserves the named state volume
```

To update an existing VPS installation to show seconds:

```bash
git pull --ff-only
# Preserve the existing token and channel ID; change only the refresh interval:
sed -i 's/^UPDATE_INTERVAL_SECONDS=.*/UPDATE_INTERVAL_SECONDS=15/' .env
docker compose up -d --build --force-recreate
docker compose logs --tail=30 -f
```

This edits the existing countdown message, so the pinned message and its link remain the same. While the embed visibly includes seconds, the digits update every ~15 seconds, not continuously. For a smooth every-second display, use the [website](https://migtam628.github.io/gta-vi/) or share it on a Discord video stream.

Run only one instance in the same Discord channel. Avoid `docker compose down -v`, which deletes the message-ID volume. To relocate the countdown to another channel, change `DISCORD_CHANNEL_ID` and restart; the bot will create a new message there.

## Troubleshooting

- **Bot offline:** Check `docker compose logs`, the token, and VPS internet access.
- **Forbidden / missing access:** Grant View Channel, Send Messages, Embed Links, and Read Message History in the selected channel. Manage Messages is needed only to pin.
- **No post appears:** Confirm `DISCORD_CHANNEL_ID` is the **text channel** ID, not the server or event ID.
- **Two messages:** Stop duplicate bot containers, remove the extra message, and keep only one process active.
- **Token exposed:** Reset it immediately in the Developer Portal, then update your local `.env`.

This bot uses no Message Content or Members privileged gateway intents.

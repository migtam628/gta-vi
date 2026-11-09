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

## Spanish version / Versión en español

The countdown supports both English and Spanish. English stays the default; switch only the Discord embed to Spanish by adding `COUNTDOWN_LANGUAGE=es` in your existing `.env` file. The date, seconds, event buttons, Discord channel, token, and saved message ID stay unchanged. The Spanish Discord button links to the Spanish countdown page.

The website has a language toggle:
- English: https://migtam628.github.io/gta-vi/
- Español: https://migtam628.github.io/gta-vi/es/

### Activate Spanish on the VPS

```bash
cd ~/gta-vi/discord-bot
git pull --ff-only
# Add or update the language setting WITHOUT replacing .env or its secrets:
if grep -q '^COUNTDOWN_LANGUAGE=' .env; then
  sed -i 's/^COUNTDOWN_LANGUAGE=.*/COUNTDOWN_LANGUAGE=es/' .env
else
  printf '\nCOUNTDOWN_LANGUAGE=es\n' >> .env
fi
docker compose up -d --build --force-recreate
docker compose logs --tail=20 -f
```

To switch back to English, replace `COUNTDOWN_LANGUAGE=es` with `COUNTDOWN_LANGUAGE=en` and recreate the container. The bot edits its **existing countdown message**, so its Discord link and any pin remain intact. Discord's relative timestamp is translated automatically according to each viewer's Discord locale.

## Automatic language selection

The **website** now detects the visitor's device/browser language using the preferred browser language (no location permission, IP tracking, or geolocation). Visitors preferring Spanish who open the main URL are redirected to `/es/`. All other languages currently fall back to English. Visitors can choose English or Español manually, and their preference is remembered on that browser.

The **Discord public countdown** is a single shared message; Discord does not translate the same bot embed automatically for each member. The new **🌍 My language / Mi idioma** button reads the Discord language of the member who clicks it (`interaction.locale`) and sends that person a private, temporary Spanish or English countdown embed, along with event and website links. Spanish Discord locales (`es-ES`, `es-419`, etc.) receive Spanish; others receive English. It does not discover physical location or inspect Discord member profiles.

The original `COUNTDOWN_LANGUAGE=en|es` setting still controls the **shared public embed**, not the personal translations. The website and the Discord per-user view work independently.

### Deploy to the VPS

```bash
cd ~/gta-vi/discord-bot
git pull --ff-only
docker compose up -d --build --force-recreate
docker compose logs --tail=30 -f
```

The new 🌍 button is added to the **same existing Discord message**, preserving its pin and link. Existing `.env` secrets are preserved. If the shared message is in Spanish today it stays Spanish, while each member's button displays the selected translation privately. To change the default public language, set `COUNTDOWN_LANGUAGE=en` or `COUNTDOWN_LANGUAGE=es` in `.env` and recreate the container.


## Launch-week channel starters

There are **six reviewed, bilingual English/Spanish starter posts** in `channel_seed_posts.json`: announcements, general chat, predictions, challenges, media, and spoiler rules. The live `#launch-countdown` bot is already managing that channel and is intentionally left untouched. The `ROAD_TO_VICE_CITY.md` file contains a daily activity calendar.

The publishing tool is **preview-first**: simply running it never sends anything. It sends messages only when `--publish` is included, and stores the posted message IDs in the existing Docker named volume to avoid duplicating posts on repeated runs.

**On your VPS:**

```bash
cd ~/gta-vi/discord-bot
git pull --ff-only
docker compose up -d --build --force-recreate

# Preview six posts; no messages are sent:
docker compose exec -T countdown-bot python seed_channels.py

# Only when ready, publish one starter post per channel:
docker compose exec -T countdown-bot python seed_channels.py --publish
```

Or preview/publish only one channel:

```bash
docker compose exec -T countdown-bot python seed_channels.py --only gta6-general
docker compose exec -T countdown-bot python seed_channels.py --publish --only gta6-general
```

The bot needs **View Channel**, **Send Messages**, and **Embed Links** for the target channels, and permission to create a post in a Forum/Media channel. `#gta6-media` may be a Discord Media channel, so the tool automatically creates a media/forum **thread post**, not an invalid ordinary text message. If any required tag is configured on a media/forum channel, the tool stops **before posting anything** and asks you to address that channel setting; it does not guess which tag to use.

The tool uses the bot token from your existing private `.env`. It does not print your token or enable `@everyone` pings. It posts to the **Mig's World server only** (`866125624656789514`). To change the content, edit the reviewed JSON file in GitHub and rebuild before publishing. If a publish run partially succeeds, the recorded posts are skipped on a rerun.

## Full bilingual publishing / Publicaciones completas en ambos idiomas

**English:** All six starter posts now contain **complete English and Spanish sections**. The shared public countdown supports **`COUNTDOWN_LANGUAGE=bi`** to display both languages in one message. Private per-member translations and website language detection remain available.

**Español:** Las seis publicaciones iniciales ahora incluyen **versiones completas en inglés y español**. La cuenta regresiva pública admite **`COUNTDOWN_LANGUAGE=bi`** para mostrar ambos idiomas en un mismo mensaje. También siguen disponibles las traducciones privadas y la detección automática del idioma en la web.

**To activate / Para activar:**

```bash
cd ~/gta-vi/discord-bot
git pull --ff-only
# Keep the existing token and channel ID; update only the public embed language.
if grep -q '^COUNTDOWN_LANGUAGE=' .env; then
  sed -i 's/^COUNTDOWN_LANGUAGE=.*/COUNTDOWN_LANGUAGE=bi/' .env
else
  printf '\nCOUNTDOWN_LANGUAGE=bi\n' >> .env
fi
docker compose up -d --build --force-recreate
```

**Preview bilingual posts / Vista previa en ambos idiomas (no publishing):**

```bash
docker compose exec -T countdown-bot python seed_channels.py
```

**Publish new posts / Publicar mensajes nuevos (after granting bot permissions in the channels):**

```bash
docker compose exec -T countdown-bot python seed_channels.py --publish
```

**Update existing tracked posts / Actualizar publicaciones existentes sin duplicarlas:**

```bash
docker compose exec -T countdown-bot python seed_channels.py --publish --update
```

**Permission error / Error de permisos:** `403 Missing Permissions / 50013` means the bot can authenticate, but cannot publish in a selected channel. Check **Edit Channel → Permissions** for the bot role: **View Channel, Send Messages, Embed Links, Read Message History**. For a Forum/Media channel also allow creating posts and sending messages in threads. Check parent-category Deny overrides. The publishing script now prints the **exact failing channel name and ID**. It never uses administrator privileges or unsolicited mass mentions.

**English:** The script does **not** modify the existing live countdown and remembers already published IDs in its Docker named volume. If the original posts were already published, use `--publish --update`; if none were published, use `--publish` after fixing permissions. Never use `docker compose down -v` because it erases the state volume.

**Español:** El script **no modifica** la cuenta regresiva actual y guarda los IDs de los mensajes publicados en el volumen de Docker. Si los mensajes originales ya se publicaron, usa `--publish --update`; si aún no hay ninguno, usa `--publish` después de corregir los permisos. Evita `docker compose down -v` porque borra el volumen de estado.

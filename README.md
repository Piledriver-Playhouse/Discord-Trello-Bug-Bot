# Discord Trello Bug Bot

[![Documentation](https://img.shields.io/badge/docs-Sphinx-blue.svg)](https://Piledriver-Playhouse.github.io/Discord-Trello-Bug-Bot/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Docker Pulls](https://img.shields.io/badge/docker-ghcr.io-blue.svg)](https://github.com/Piledriver-Playhouse/Discord-Trello-Bug-Bot/pkgs/container/discord-trello-bug-bot)

A lightweight Discord bot that turns `!bug` messages into Trello cards — built for private game repositories by **Piledriver Playhouse** where public GitHub Issues aren't desired.

## What It Does

1. A user types `!bug <report>` in a designated Discord channel.
2. The bot creates a Trello card in a configured list (e.g., **Bugs**) with the full report, reporter info, and a link back to the Discord message.
3. The bot reacts with ✅ and replies with the Trello card URL.

No database, no web server, no inbound webhooks just an outbound connection to Discord and Trello.

---

## Features

- 🐛 Discord command-based bug reports (`!bug`)
- 📋 Automatic Trello card creation
- 🐳 Docker & Docker Compose support
- ☸️ k3s / Kubernetes deployment manifests
- 🔒 No database, no persistent storage, no public endpoints
- ⚙️ Fully configured via environment variables

---

## Discord Setup

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Click **New Application** and give it a name (e.g. `Bug Bot`).
3. Go to **Bot** in the sidebar and click **Add Bot**.
4. Copy the **Bot Token** — you'll need this as `DISCORD_TOKEN`.
5. Scroll down and **enable the Message Content Intent** toggle under *Privileged Gateway Intents*.
6. Go to **OAuth2 → URL Generator**.
   - Under *Scopes*, select **bot**.
   - Under *Bot Permissions*, select:
     - View Channels
     - Read Message History
     - Send Messages
     - Add Reactions
   - Copy the generated URL and open it in your browser to invite the bot to your server.

### Getting the Channel ID

1. Open Discord **Settings → Advanced** and enable **Developer Mode**.
2. Right-click the channel you want the bot to watch.
3. Click **Copy Channel ID**.
4. Use this value as `BUG_CHANNEL_ID`.

---

## Trello Setup

### 1. Get your API Key

1. Go to [https://trello.com/power-ups/admin](https://trello.com/power-ups/admin).
2. Create a new Power-Up (or use an existing one).
3. Navigate to the **API Key** section and copy your key → `TRELLO_API_KEY`.

### 2. Generate a Token

1. On the same API Key page, click the link to **generate a Token** (or visit `https://trello.com/1/authorize?expiration=never&scope=read,write&response_type=token&key=YOUR_API_KEY`).
2. Authorize and copy the token → `TRELLO_TOKEN`.

### 3. Create a Board and List

1. Create or open a Trello board.
2. Add a list called **Bugs** (or whatever you prefer).

### 4. Get the List ID

**Method A — Board JSON (easiest):**

1. Open your Trello board in a browser.
2. Add `.json` to the end of the URL, e.g.:
   ```
   https://trello.com/b/ABC123/my-board.json
   ```
3. Search the JSON for `"name":"Bugs"` (or your list name).
4. Copy the `"id"` value next to it → `TRELLO_LIST_ID`.

**Method B — Trello API:**

```bash
curl "https://api.trello.com/1/boards/BOARD_ID/lists?key=YOUR_KEY&token=YOUR_TOKEN" | python -m json.tool
```

Find the list named "Bugs" and copy its `id`.

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DISCORD_TOKEN` | ✅ | — | Discord bot token |
| `BUG_CHANNEL_ID` | ✅ | — | Discord channel ID to listen in |
| `TRELLO_API_KEY` | ✅ | — | Trello API key |
| `TRELLO_TOKEN` | ✅ | — | Trello authorization token |
| `TRELLO_LIST_ID` | ✅ | — | Trello list ID for new cards |
| `COMMAND_PREFIX` | ❌ | `!` | Bot command prefix |
| `CARD_TITLE_PREFIX` | ❌ | `Bug:` | Prefix for Trello card titles |
| `LOG_LEVEL` | ❌ | `INFO` | Python log level |

---

## Local Setup

```bash
# Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Linux / macOS
# .venv\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your real values
```

The bot uses [python-dotenv](https://pypi.org/project/python-dotenv/) to load `.env` automatically when running locally.

## Run Locally

```bash
python bot.py
```

---

## Run with Docker

```bash
# Build
docker build -t arcascian-bugbot:latest .

# Run
docker run --env-file .env arcascian-bugbot:latest
```

## Run with Docker Compose

```bash
docker compose up --build
```

The Compose file reads from `.env` in the project root.

---

## Publish Image to GitHub Container Registry

```bash
# Log in (once)
echo $GHCR_TOKEN | docker login ghcr.io -u YOUR_USERNAME --password-stdin

# Build and push
docker build -t ghcr.io/piledriver-playhouse/discord-trello-bug-bot:latest .
docker push ghcr.io/piledriver-playhouse/discord-trello-bug-bot:latest
```

---

## Deploy to Kubernetes & GitOps

The bot is designed to run seamlessly in a Kubernetes cluster (e.g., k3s) and plays well with GitOps tools like **ArgoCD**.

### 1. Secrets Management
ArgoCD and GitOps repositories should not store plain text secrets. You must create the secret manually (or via SealedSecrets) on your cluster:

```bash
kubectl create namespace arcascian-tools
kubectl -n arcascian-tools create secret generic arcascian-bugbot-secrets \
  --from-literal=DISCORD_TOKEN='...' \
  --from-literal=BUG_CHANNEL_ID='...' \
  --from-literal=TRELLO_API_KEY='...' \
  --from-literal=TRELLO_TOKEN='...' \
  --from-literal=TRELLO_LIST_ID='...'
```

### 2. Private Image Pull Secret (Optional)
If your GHCR package is private, create a Docker registry secret and update `deployment.yaml` with an `imagePullSecrets` configuration:
```bash
kubectl -n arcascian-tools create secret docker-registry ghcr-secret \
  --docker-server=ghcr.io \
  --docker-username=YOUR_USERNAME \
  --docker-password='...' \
  --docker-email=info@piledriver-playhouse.com
```

### 3. Deploy
Apply the deployment manifests natively or via ArgoCD:
```bash
kubectl apply -f k8s/deployment.yaml
```

> **Note:** The bot only makes outbound connections, so no Service or Ingress is needed. The `deployment.yaml` restricts the pod to `amd64` nodes to prevent `exec format error` on ARM architectures.

---

## Usage

In the configured Discord channel, type:

```
!bug Game crashes after selecting upgrade at the end of a floor
```

```
!bug Platform: Windows | Mode: Online client | Issue: Client freezes after upgrade selection
```

The bot will:
- React to your message with ✅
- Reply with a link to the new Trello card

If something goes wrong, it reacts with ❌ and replies with an error message.

---

## Troubleshooting

### Bot does not respond
- Verify the bot is invited to the server.
- Check `BUG_CHANNEL_ID` matches the channel you're posting in.
- Ensure **Message Content Intent** is enabled in the Developer Portal.
- Confirm the bot has *View Channels*, *Read Message History*, *Send Messages*, and *Add Reactions* permissions.

### Trello card not created
- Verify `TRELLO_API_KEY` and `TRELLO_TOKEN` are correct and not expired.
- Verify `TRELLO_LIST_ID` is a valid list ID on your board.
- Check the bot logs for the full error.

### Bot works locally but not in k3s
- Verify the secret name matches `arcascian-bugbot-secrets`.
- Ensure all required env vars are present in the secret.
- Confirm the image name in `deployment.yaml` matches what you pushed.
- Check pod logs: `kubectl -n arcascian-tools logs deploy/arcascian-bugbot`

### discord.py privileged intent error
- Go to the [Developer Portal](https://discord.com/developers/applications), select your app → **Bot**, and enable **Message Content Intent**.

---

## Security Notes

- **Never commit `.env`** — it's in `.gitignore` for a reason.
- **Never commit real values** in `k8s/secret.example.yaml`.
- **Rotate credentials immediately** if your Discord token or Trello API key/token is exposed.
- Be careful with `docker login` credentials and GitHub Actions secrets when pushing images.

---

## Suggested Discord Channel Message

Pin this in your bug-report channel:

> **Found a bug?**
>
> Use:
> `!bug <describe the issue>`
>
> Please include platform, mode, what happened, what you expected, and reproduction steps if possible.

---

## Documentation

Full Sphinx-generated documentation is available at [https://Piledriver-Playhouse.github.io/Discord-Trello-Bug-Bot/](https://Piledriver-Playhouse.github.io/Discord-Trello-Bug-Bot/).

The documentation is automatically deployed on every push to `main` via the `.github/workflows/docs.yml` GitHub Action.

### Build Docs Locally

```bash
# Install Sphinx and theme dependencies
pip install -r docs/requirements.txt

# Build HTML output
sphinx-build -b html docs/ docs/_build/html

# Open in browser
open docs/_build/html/index.html   # macOS
xdg-open docs/_build/html/index.html  # Linux
```

---

## License

This project is licensed under the MIT License. See the [LICENSE](./LICENSE) file for details.

Copyright (c) 2026 Piledriver Playhouse.

"""
Discord Trello Bug Bot
======================

A lightweight Discord bot that listens for ``!bug`` commands in a
configured channel and creates corresponding Trello cards via the
Trello REST API.

Intended for private game development teams who need a simple bug
reporting pipeline without exposing public GitHub Issues.

Architecture
------------
- **Discord gateway** — connects via :mod:`discord.py <discord>` using
  the Message Content privileged intent.
- **Trello REST API** — creates cards asynchronously using
  :mod:`aiohttp`.
- **Configuration** — all settings are read from environment variables
  (loaded from ``.env`` locally via :mod:`python-dotenv <dotenv>`).

Module-level Configuration
--------------------------
After :func:`load_config` runs at import time, a :class:`BotConfig`
instance is available as :data:`config`, holding all required and
optional settings.

Usage
-----
.. code-block:: bash

    python bot.py
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import aiohttp
import discord
from discord.ext import commands
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Configuration data class
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BotConfig:
    """Immutable container for all bot configuration values.

    All fields are populated by :func:`load_config` at import time.
    The dataclass is frozen to prevent accidental mutation after
    initialisation.
    """

    discord_token: str          #: Bot token from the Discord Developer Portal.
    bug_channel_id: int         #: Numeric channel ID where ``!bug`` is listened for.
    trello_api_key: str         #: Trello API key from the Power-Ups admin page.
    trello_token: str           #: Trello authorisation token with read/write scope.
    trello_list_id: str         #: ID of the Trello list where cards are created.
    command_prefix: str         #: Prefix character(s) for Discord commands.
    card_title_prefix: str      #: String prepended to every Trello card title.
    log_level: str              #: Python logging level name (e.g. ``"INFO"``).
    enable_threads: bool        #: Whether to automatically create a Discord thread for each bug.
    enable_attachments: bool    #: Whether to sync Discord attachments to the Trello card.
    trello_done_list_id: str | None #: Optional list ID to watch for "Fixed" cards.
    webhook_host: str           #: Interface for the webhook server to bind to.
    webhook_port: int           #: Port for the webhook server to listen on.


# ---------------------------------------------------------------------------
# Configuration loading
# ---------------------------------------------------------------------------

#: Environment variable names that **must** be set for the bot to start.
REQUIRED_ENV: list[str] = [
    "DISCORD_TOKEN",
    "BUG_CHANNEL_ID",
    "TRELLO_API_KEY",
    "TRELLO_TOKEN",
    "TRELLO_LIST_ID",
]


def validate_env(required: list[str]) -> list[str]:
    """Check that all *required* environment variables are set.

    Args:
        required: List of environment variable names to check.

    Returns:
        A list of variable names that are **missing** (empty list if
        all are present).
    """
    return [var for var in required if not os.getenv(var)]


def load_config() -> BotConfig:
    """Load and validate bot configuration from environment variables.

    Calls :func:`dotenv.load_dotenv` first so that a local ``.env``
    file is picked up automatically.  In Docker / Kubernetes the
    variables are injected by the runtime so ``load_dotenv`` is a
    harmless no-op.

    Returns:
        A populated :class:`BotConfig` instance.

    Raises:
        SystemExit: If any required variable is missing.
    """
    # Load .env file (no-op in Docker / k8s where vars are injected).
    load_dotenv()

    missing: list[str] = validate_env(REQUIRED_ENV)
    if missing:
        print(
            f"FATAL: Missing required environment variable(s): "
            f"{', '.join(missing)}",
            file=sys.stderr,
        )
        sys.exit(1)

    return BotConfig(
        discord_token=os.environ["DISCORD_TOKEN"],
        bug_channel_id=int(os.environ["BUG_CHANNEL_ID"]),
        trello_api_key=os.environ["TRELLO_API_KEY"],
        trello_token=os.environ["TRELLO_TOKEN"],
        trello_list_id=os.environ["TRELLO_LIST_ID"],
        command_prefix=os.getenv("COMMAND_PREFIX", "!"),
        card_title_prefix=os.getenv("CARD_TITLE_PREFIX", "Bug:"),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        enable_threads=os.getenv("ENABLE_THREADS", "true").lower() == "true",
        enable_attachments=os.getenv("ENABLE_ATTACHMENTS", "true").lower() == "true",
        trello_done_list_id=os.getenv("TRELLO_DONE_LIST_ID"),
        webhook_host=os.getenv("WEBHOOK_HOST", "0.0.0.0"),
        webhook_port=int(os.getenv("WEBHOOK_PORT", "8080")),
    )


# ---------------------------------------------------------------------------
# Initialise configuration and logging
# ---------------------------------------------------------------------------

config: BotConfig = load_config()
"""Module-level :class:`BotConfig` instance, populated at import time."""

# ---------------------------------------------------------------------------
# Stats and Logging Interception
# ---------------------------------------------------------------------------

from collections import deque


@dataclass
class BotStats:
    """Track runtime statistics for the dashboard."""
    start_time: datetime = datetime.now(timezone.utc)
    bugs_reported: int = 0
    attachments_synced: int = 0
    threads_created: int = 0
    last_bug_at: datetime | None = None


stats = BotStats()


class LogCaptureHandler(logging.Handler):
    """Custom logging handler to store the last 100 log lines in memory."""
    def __init__(self, capacity: int = 100) -> None:
        super().__init__()
        self.logs: deque[str] = deque(maxlen=capacity)

    def emit(self, record: logging.LogRecord) -> None:
        msg: str = self.format(record)
        self.logs.append(msg)


log_capture = LogCaptureHandler()
log_capture.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logging.getLogger().addHandler(log_capture)

logging.basicConfig(
    level=getattr(logging, config.log_level, logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
log: logging.Logger = logging.getLogger("bugbot")

# ---------------------------------------------------------------------------
# Trello helpers
# ---------------------------------------------------------------------------

#: Trello REST API endpoint for creating cards.
TRELLO_CARDS_URL: str = "https://api.trello.com/1/cards"


async def create_trello_card(
    session: aiohttp.ClientSession,
    name: str,
    desc: str,
) -> dict[str, Any]:
    """Create a new card on the configured Trello list.

    Sends a ``POST`` request to the Trello REST API and returns the
    full JSON response on success.

    Args:
        session: An active :class:`aiohttp.ClientSession`.
        name: Card title (appears as the card heading in Trello).
        desc: Card description (Trello supports Markdown).

    Returns:
        The parsed JSON response dictionary from Trello, which
        includes keys such as ``shortUrl``, ``url``, ``id``, etc.

    Raises:
        aiohttp.ClientResponseError: If the Trello API returns a
            non-2xx status code.
    """
    params: dict[str, str] = {
        "key": config.trello_api_key,
        "token": config.trello_token,
        "idList": config.trello_list_id,
        "name": name,
        "desc": desc,
    }
    async with session.post(TRELLO_CARDS_URL, params=params) as resp:
        resp.raise_for_status()
        data: dict[str, Any] = await resp.json()
        return data


async def add_attachment_to_trello_card(
    session: aiohttp.ClientSession,
    card_id: str,
    url: str,
) -> None:
    """Upload an external file (via URL) as an attachment to a Trello card.

    Args:
        session: An active :class:`aiohttp.ClientSession`.
        card_id: The ID of the Trello card to attach the file to.
        url: The public URL of the file to attach.

    Raises:
        aiohttp.ClientResponseError: If the Trello API returns a
            non-2xx status code.
    """
    api_url: str = f"{TRELLO_CARDS_URL}/{card_id}/attachments"
    params: dict[str, str] = {
        "key": config.trello_api_key,
        "token": config.trello_token,
        "url": url,
    }
    async with session.post(api_url, params=params) as resp:
        resp.raise_for_status()


# ---------------------------------------------------------------------------
# Card content builders
# ---------------------------------------------------------------------------

#: Maximum number of characters from the report used in the card title.
TITLE_MAX_LENGTH: int = 80


def build_card_title(report: str) -> str:
    """Build a Trello card title from a bug report.

    The title is the configured :attr:`~BotConfig.card_title_prefix`
    followed by the first :data:`TITLE_MAX_LENGTH` characters of the
    report text.

    Args:
        report: The full bug report text.

    Returns:
        A formatted card title string, e.g. ``"Bug: Game crashes …"``.
    """
    return f"{config.card_title_prefix} {report[:TITLE_MAX_LENGTH]}"


def build_card_description(
    report: str,
    author: discord.User | discord.Member,
    channel_name: str,
    message_link: str,
) -> str:
    """Build a Trello card description with full report and metadata.

    The description includes the complete bug report text followed by
    a metadata block containing the reporter's Discord username, user
    ID, channel name, a link to the original message, and a UTC
    timestamp.

    Args:
        report: The full bug report text.
        author: The Discord user who submitted the report.
        channel_name: Name of the Discord channel.
        message_link: Jump URL linking back to the Discord message.

    Returns:
        A Markdown-formatted description string ready for Trello.
    """
    timestamp: str = datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )
    return (
        f"**Bug Report**\n\n"
        f"{report}\n\n"
        f"---\n"
        f"**Reporter:** {author} (`{author.id}`)\n"
        f"**Channel:** #{channel_name}\n"
        f"**Message:** {message_link}\n"
        f"**Timestamp:** {timestamp}\n"
    )


# ---------------------------------------------------------------------------
# Discord bot setup
# ---------------------------------------------------------------------------


def create_bot(prefix: str) -> commands.Bot:
    """Create and configure a :class:`~discord.ext.commands.Bot` instance.

    Enables the ``message_content`` privileged intent so the bot can
    read message text and parse prefix commands.

    Args:
        prefix: The command prefix string (e.g. ``"!"``).

    Returns:
        A configured :class:`~discord.ext.commands.Bot` ready for
        command registration.
    """
    intents: discord.Intents = discord.Intents.default()
    intents.message_content = True  # Requires Message Content privileged intent
    return commands.Bot(command_prefix=prefix, intents=intents)


bot: commands.Bot = create_bot(config.command_prefix)
"""The global :class:`~discord.ext.commands.Bot` instance."""


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------


@bot.event
async def on_ready() -> None:
    """Handle the Discord ``READY`` event.

    Logs the bot's username, user ID, and the channel/prefix it is
    configured to listen on. Fired once after the bot has connected
    to the Discord gateway and received initial state.
    """
    assert bot.user is not None  # guaranteed after READY
    log.info("Logged in as %s (ID: %s)", bot.user, bot.user.id)
    log.info(
        "Listening for %sbug in channel %s",
        config.command_prefix,
        config.bug_channel_id,
    )


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@bot.command(name="bug")
async def bug_command(
    ctx: commands.Context[commands.Bot],
    *,
    report: str | None = None,
) -> None:
    """Handle the ``!bug`` command and create a Trello card.

    Workflow:

    1. Ignore messages outside the configured channel.
    2. If no report text is provided, reply with usage help.
    3. Build a Trello card title and description via
       :func:`build_card_title` and :func:`build_card_description`.
    4. ``POST`` the card to Trello via :func:`create_trello_card`.
    5. On success — react ✅ and reply with the card URL.
    6. On failure — react ❌, reply with an error message, and log
       the full exception traceback.

    Args:
        ctx: The Discord command invocation context.
        report: The bug report text following ``!bug``.  ``None`` if
            the user invoked the command with no arguments.
    """
    # ── Guard: only respond in the configured channel ──────────────────
    if ctx.channel.id != config.bug_channel_id:
        return

    # ── Guard: no report text provided ─────────────────────────────────
    if not report or not report.strip():
        await ctx.reply(
            f"**Usage:** `{config.command_prefix}bug <describe the issue>`\n"
            "Please include platform, mode, what happened, "
            "what you expected, and reproduction steps if possible."
        )
        return

    report = report.strip()

    # ── Build card content ─────────────────────────────────────────────
    card_title: str = build_card_title(report)
    card_desc: str = build_card_description(
        report=report,
        author=ctx.author,
        channel_name=getattr(ctx.channel, "name", "DM"),
        message_link=ctx.message.jump_url,
    )

    # ── Create the Trello card ─────────────────────────────────────────
    try:
        async with aiohttp.ClientSession() as session:
            card: dict[str, Any] = await create_trello_card(
                session, card_title, card_desc
            )

            # Prefer the short URL; fall back to the full URL.
            card_url: str | None = card.get("shortUrl") or card.get("url")
            card_id: str | None = card.get("id")

            stats.bugs_reported += 1
            stats.last_bug_at = datetime.now(timezone.utc)

            log.info(
                "Card created for %s (%s): %s",
                ctx.author,
                ctx.author.id,
                card_url,
            )

            # ── Handle Attachments ─────────────────────────────────────────
            if config.enable_attachments and ctx.message.attachments and card_id:
                for attachment in ctx.message.attachments:
                    try:
                        await add_attachment_to_trello_card(
                            session, card_id, attachment.url
                        )
                        stats.attachments_synced += 1
                        log.info("Attached file to Trello: %s", attachment.filename)
                    except Exception as att_exc:
                        log.warning(
                            "Failed to upload attachment %s: %s",
                            attachment.filename,
                            att_exc,
                        )

            # Success feedback in Discord.
            await ctx.message.add_reaction("✅")
            await ctx.reply(f"Bug report submitted! Trello card: {card_url}")

            # ── Handle Thread Creation ─────────────────────────────────────
            if config.enable_threads:
            try:
                # Thread name should be somewhat descriptive.
                thread_name: str = (
                    f"Bug: {report[:50]}..." if len(report) > 50 else f"Bug: {report}"
                )
                await ctx.message.create_thread(
                    name=thread_name, auto_archive_duration=1440
                )
                stats.threads_created += 1
                log.info("Created Discord thread for bug report.")
            except Exception as thread_exc:
                log.warning("Failed to create Discord thread: %s", thread_exc)

    except Exception as exc:
        # Log the full traceback for debugging.
        log.error("Failed to create Trello card: %s", exc, exc_info=True)

        # Failure feedback in Discord.
        await ctx.message.add_reaction("❌")
        await ctx.reply(
            "⚠️ Failed to create the Trello card. "
            "Please try again or notify an admin."
        )


# ---------------------------------------------------------------------------
# Webhook Receiver (Trello -> Discord)
# ---------------------------------------------------------------------------

import re
import asyncio
import aiohttp_jinja2
import jinja2
from aiohttp import web
from datetime import datetime, timezone, timedelta

#: Regex to extract the message link from a Trello card description.
MESSAGE_LINK_RE: re.Pattern[str] = re.compile(
    r"\*\*Message:\*\* (https://discord\.com/channels/\d+/\d+/\d+)"
)


async def handle_trello_webhook(request: web.Request) -> web.Response:
    """Process incoming Trello webhooks.

    Trello sends a ``HEAD`` request to verify the webhook URL on
    creation. Subsequent notifications are ``POST`` requests with a
    JSON payload.

    If a card is moved to the list matching
    :attr:`~BotConfig.trello_done_list_id`, the bot attempts to find
    the original Discord message and post a "Fixed" notification.
    """
    # Trello head request for webhook validation.
    if request.method == "HEAD":
        return web.Response(status=200)

    try:
        data: dict[str, Any] = await request.json()
        action: dict[str, Any] = data.get("action", {})
        
        # Check if the action is moving a card to the "Done" list.
        if (
            action.get("type") == "updateCard" and
            action.get("display", {}).get("translationKey") == "action_move_card_from_list_to_list" and
            action.get("data", {}).get("listAfter", {}).get("id") == config.trello_done_list_id
        ):
            card_data: dict[str, Any] = action.get("data", {}).get("card", {})
            card_id: str = card_data.get("id", "Unknown")
            card_name: str = card_data.get("name", "Unknown Bug")
            
            # We need to get the full card description to find the Discord link.
            # This requires one extra API call.
            async with aiohttp.ClientSession() as session:
                params: dict[str, str] = {
                    "key": config.trello_api_key,
                    "token": config.trello_token,
                }
                async with session.get(f"{TRELLO_CARDS_URL}/{card_id}", params=params) as resp:
                    if resp.status == 200:
                        card_detail: dict[str, Any] = await resp.json()
                        desc: str = card_detail.get("desc", "")
                        match: re.Match[str] | None = MESSAGE_LINK_RE.search(desc)
                        
                        if match:
                            msg_url: str = match.group(1)
                            # URL format: https://discord.com/channels/GUILD_ID/CHANNEL_ID/MESSAGE_ID
                            parts: list[str] = msg_url.split("/")
                            channel_id: int = int(parts[-2])
                            message_id: int = int(parts[-1])
                            
                            channel: Any = bot.get_channel(channel_id)
                            if channel:
                                # If it was a thread, we can post there.
                                # If not, we reply to the original message.
                                try:
                                    message: discord.Message = await channel.fetch_message(message_id)
                                    # Post "Fixed" notification.
                                    fixed_msg: str = (
                                        f"🎉 **Bug Fixed!**\n"
                                        f"Trello card **\"{card_name}\"** has been moved to Fixed."
                                    )
                                    if message.thread:
                                        await message.thread.send(fixed_msg)
                                    else:
                                        await message.reply(fixed_msg)
                                    log.info("Posted fix notification for card %s", card_id)
                                except Exception as disc_exc:
                                    log.warning("Could not post to Discord: %s", disc_exc)

        return web.Response(status=200)
    except Exception as err:
        log.error("Error processing Trello webhook: %s", err)
        return web.Response(status=500)


# ---------------------------------------------------------------------------
# Dashboard Routes
# ---------------------------------------------------------------------------

@aiohttp_jinja2.template("index.html")
async def handle_dashboard(request: web.Request) -> dict[str, Any]:
    """Render the main dashboard page."""
    # Fetch recent bugs directly from Trello for the dashboard.
    recent_bugs: list[dict[str, Any]] = []
    try:
        async with aiohttp.ClientSession() as session:
            params: dict[str, str] = {
                "key": config.trello_api_key,
                "token": config.trello_token,
                "limit": "10",
            }
            async with session.get(
                f"https://api.trello.com/1/lists/{config.trello_list_id}/cards",
                params=params
            ) as resp:
                if resp.status == 200:
                    recent_bugs = await resp.json()
    except Exception as e:
        log.warning("Dashboard failed to fetch Trello cards: %s", e)

    uptime: timedelta = datetime.now(timezone.utc) - stats.start_time
    # Format uptime as H:M:S
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str: str = f"{hours:02}:{minutes:02}:{seconds:02}"

    return {
        "stats": stats,
        "uptime": uptime_str,
        "recent_bugs": recent_bugs,
        "version": "v1.1.0",
    }


async def handle_stats_api(request: web.Request) -> web.Response:
    """Return bot statistics as JSON."""
    uptime: timedelta = datetime.now(timezone.utc) - stats.start_time
    return web.json_response({
        "uptime": str(uptime),
        "bugs_reported": stats.bugs_reported,
        "attachments_synced": stats.attachments_synced,
        "threads_created": stats.threads_created,
        "last_bug_at": stats.last_bug_at.isoformat() if stats.last_bug_at else None,
    })


async def handle_log_stream(request: web.Request) -> web.Response:
    """Stream live logs to the browser using Server-Sent Events (SSE)."""
    response = web.StreamResponse(
        status=200,
        reason="OK",
        headers={
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
    await response.prepare(request)

    # Send initial logs.
    for line in log_capture.logs:
        await response.write(f"data: {line}\n\n".encode("utf-8"))

    # Keep the connection open and wait for new logs.
    # Simple implementation: poll log_capture.logs for changes.
    last_log_count: int = len(log_capture.logs)
    while True:
        await asyncio.sleep(1)
        current_logs = list(log_capture.logs)
        if len(current_logs) > last_log_count:
            # Send only the new lines.
            new_lines = current_logs[last_log_count:]
            for line in new_lines:
                await response.write(f"data: {line}\n\n".encode("utf-8"))
            last_log_count = len(current_logs)

    return response


async def run_webhook_server() -> None:
    """Run the aiohttp web server for incoming webhooks and dashboard."""
    app: web.Application = web.Application()
    
    # Setup Jinja2 templates.
    aiohttp_jinja2.setup(
        app, loader=jinja2.FileSystemLoader("templates")
    )

    app.router.add_get("/", handle_dashboard)
    app.router.add_get("/api/stats", handle_stats_api)
    app.router.add_get("/api/logs", handle_log_stream)
    app.router.add_route("*", "/trello-webhook", handle_trello_webhook)
    
    runner: web.AppRunner = web.AppRunner(app)
    await runner.setup()
    site: web.TCPSite = web.TCPSite(
        runner, config.webhook_host, config.webhook_port
    )
    await site.start()
    log.info(
        "Webhook and Dashboard server listening on %s:%s",
        config.webhook_host,
        config.webhook_port
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Start the Discord bot and the webhook server.

    Prints a minimal startup banner to stdout and then starts the
    asyncio event loop to run both the Discord bot and the aiohttp
    web server concurrently.
    """
    print(
        f"Starting bug bot "
        f"(prefix={config.command_prefix!r}, "
        f"channel={config.bug_channel_id})"
    )

    import asyncio

    async def start_everything() -> None:
        # Start the webhook server.
        await run_webhook_server()
        # Start the Discord bot.
        # We use start() instead of run() to avoid blocking the loop.
        try:
            await bot.start(config.discord_token)
        finally:
            if not bot.is_closed():
                await bot.close()

    try:
        asyncio.run(start_everything())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

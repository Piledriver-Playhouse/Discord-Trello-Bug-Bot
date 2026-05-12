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
    )


# ---------------------------------------------------------------------------
# Initialise configuration and logging
# ---------------------------------------------------------------------------

config: BotConfig = load_config()
"""Module-level :class:`BotConfig` instance, populated at import time."""

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
        log.info(
            "Card created for %s (%s): %s",
            ctx.author,
            ctx.author.id,
            card_url,
        )

        # Success feedback in Discord.
        await ctx.message.add_reaction("✅")
        await ctx.reply(f"Bug report submitted! Trello card: {card_url}")

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
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Start the Discord bot.

    Prints a minimal startup banner to stdout and then hands control
    to :meth:`discord.ext.commands.Bot.run`, which blocks until the
    bot disconnects.

    ``log_handler=None`` is passed so that :func:`logging.basicConfig`
    (configured above) takes precedence over discord.py's default
    handler.
    """
    print(
        f"Starting bug bot "
        f"(prefix={config.command_prefix!r}, "
        f"channel={config.bug_channel_id})"
    )
    bot.run(config.discord_token, log_handler=None)


if __name__ == "__main__":
    main()

"""
Configuration Module
====================

Handles loading, validation, and storage of bot settings from environment variables.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass(frozen=True, slots=True)
class BotConfig:
    """Immutable container for all bot configuration values."""

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


REQUIRED_ENV: list[str] = [
    "DISCORD_TOKEN",
    "BUG_CHANNEL_ID",
    "TRELLO_API_KEY",
    "TRELLO_TOKEN",
    "TRELLO_LIST_ID",
]


def validate_env(required: list[str]) -> list[str]:
    """Check that all required environment variables are set."""
    return [var for var in required if not os.getenv(var)]


def load_config() -> BotConfig:
    """Load and validate bot configuration from environment variables."""
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

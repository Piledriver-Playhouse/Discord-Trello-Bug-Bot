"""
Trello Integration Module
=========================

Handles all interactions with the Trello REST API.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import aiohttp
import discord

#: Trello REST API endpoint for creating cards.
TRELLO_CARDS_URL: str = "https://api.trello.com/1/cards"


async def create_trello_card(
    session: aiohttp.ClientSession,
    api_key: str,
    token: str,
    list_id: str,
    name: str,
    desc: str,
) -> dict[str, Any]:
    """Create a new card on the configured Trello list."""
    params: dict[str, str] = {
        "key": api_key,
        "token": token,
        "idList": list_id,
        "name": name,
        "desc": desc,
    }
    async with session.post(TRELLO_CARDS_URL, params=params) as resp:
        resp.raise_for_status()
        data: dict[str, Any] = await resp.json()
        return data


async def add_attachment_to_trello_card(
    session: aiohttp.ClientSession,
    api_key: str,
    token: str,
    card_id: str,
    url: str,
) -> None:
    """Upload an external file (via URL) as an attachment to a Trello card."""
    api_url: str = f"{TRELLO_CARDS_URL}/{card_id}/attachments"
    params: dict[str, str] = {
        "key": api_key,
        "token": token,
        "url": url,
    }
    async with session.post(api_url, params=params) as resp:
        resp.raise_for_status()


def build_card_title(prefix: str, report: str, max_length: int = 80) -> str:
    """Build a Trello card title from a bug report."""
    return f"{prefix} {report[:max_length]}"


def build_card_description(
    report: str,
    author: discord.User | discord.Member,
    channel_name: str,
    message_link: str,
) -> str:
    """Build a Trello card description with full report and metadata."""
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

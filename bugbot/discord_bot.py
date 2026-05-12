"""
Discord Bot Module
==================

Handles Discord gateway connection, commands, and event processing.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import aiohttp
import discord
from discord.ext import commands

from bugbot.stats import stats
from bugbot.trello import (
    add_attachment_to_trello_card,
    build_card_description,
    build_card_title,
    create_trello_card,
)

if TYPE_CHECKING:
    from bugbot.config import BotConfig

log = logging.getLogger("bugbot.discord")


def create_bot(prefix: str) -> commands.Bot:
    """Create and configure a commands.Bot instance."""
    intents: discord.Intents = discord.Intents.default()
    intents.message_content = True
    return commands.Bot(command_prefix=prefix, intents=intents)


def setup_commands(bot: commands.Bot, config: BotConfig) -> None:
    """Register commands and events on the bot instance."""

    @bot.event
    async def on_ready() -> None:
        """Handle the READY event."""
        log.info("Logged in as %s (ID: %s)", bot.user, bot.user.id)
        log.info(
            "Listening for %sbug in channel %s",
            config.command_prefix,
            config.bug_channel_id,
        )

    @bot.command(name="bug")
    async def bug_command(
        ctx: commands.Context[commands.Bot],
        *,
        report: str | None = None,
    ) -> None:
        """Handle the !bug command and create a Trello card."""
        if ctx.channel.id != config.bug_channel_id:
            return

        if not report or not report.strip():
            await ctx.reply(
                f"**Usage:** `{config.command_prefix}bug <describe the issue>`\n"
                "Please include platform, mode, what happened, "
                "reproduction steps, and any screenshots."
            )
            return

        report = report.strip()
        card_title: str = build_card_title(config.card_title_prefix, report)
        card_desc: str = build_card_description(
            report=report,
            author=ctx.author,
            channel_name=getattr(ctx.channel, "name", "DM"),
            message_link=ctx.message.jump_url,
        )

        try:
            async with aiohttp.ClientSession() as session:
                card: dict[str, Any] = await create_trello_card(
                    session=session,
                    api_key=config.trello_api_key,
                    token=config.trello_token,
                    list_id=config.trello_list_id,
                    name=card_title,
                    desc=card_desc,
                )

                card_url: str | None = card.get("shortUrl") or card.get("url")
                card_id: str | None = card.get("id")

                stats.bugs_reported += 1
                stats.last_bug_at = datetime.now(timezone.utc)

                log.info("Card created for %s: %s", ctx.author, card_url)

                # Attachments
                if config.enable_attachments and ctx.message.attachments and card_id:
                    for attachment in ctx.message.attachments:
                        try:
                            await add_attachment_to_trello_card(
                                session=session,
                                api_key=config.trello_api_key,
                                token=config.trello_token,
                                card_id=card_id,
                                url=attachment.url,
                            )
                            stats.attachments_synced += 1
                            log.info("Attached file: %s", attachment.filename)
                        except Exception as att_exc:
                            log.warning("Attachment failed: %s", att_exc)

                # Feedback
                await ctx.message.add_reaction("✅")
                await ctx.reply(f"Bug report submitted! Trello card: {card_url}")

                # Threads
                if config.enable_threads:
                    try:
                        thread_name: str = f"Bug: {report[:50]}..." if len(report) > 50 else f"Bug: {report}"
                        await ctx.message.create_thread(name=thread_name, auto_archive_duration=1440)
                        stats.threads_created += 1
                        log.info("Created thread for bug report.")
                    except Exception as thread_exc:
                        log.warning("Thread creation failed: %s", thread_exc)

        except Exception as exc:
            log.error("Failed to create Trello card: %s", exc, exc_info=True)
            await ctx.message.add_reaction("❌")
            await ctx.reply("⚠️ Failed to create the Trello card. Please notify an admin.")

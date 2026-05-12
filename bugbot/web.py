"""
Web Dashboard and Webhook Module
================================

Handles the aiohttp web server, dashboard rendering, and incoming webhooks.
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING, Any

import aiohttp
import aiohttp_jinja2
import jinja2
from aiohttp import web

from bugbot.stats import stats, log_capture
from bugbot.trello import TRELLO_CARDS_URL

if TYPE_CHECKING:
    from discord.ext import commands
    from bugbot.config import BotConfig

log = logging.getLogger("bugbot.web")

MESSAGE_LINK_RE: re.Pattern[str] = re.compile(
    r"\*\*Message:\*\* (https://discord\.com/channels/\d+/\d+/\d+)"
)


async def handle_trello_webhook(request: web.Request) -> web.Response:
    """Process incoming Trello webhooks."""
    if request.method == "HEAD":
        return web.Response(status=200)

    config: BotConfig = request.app["config"]
    bot: commands.Bot = request.app["bot"]

    try:
        data: dict[str, Any] = await request.json()
        action: dict[str, Any] = data.get("action", {})
        
        if (
            action.get("type") == "updateCard" and
            action.get("display", {}).get("translationKey") == "action_move_card_from_list_to_list" and
            action.get("data", {}).get("listAfter", {}).get("id") == config.trello_done_list_id
        ):
            card_data: dict[str, Any] = action.get("data", {}).get("card", {})
            card_id: str = card_data.get("id", "Unknown")
            card_name: str = card_data.get("name", "Unknown Bug")
            
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
                            parts: list[str] = msg_url.split("/")
                            channel_id: int = int(parts[-2])
                            message_id: int = int(parts[-1])
                            
                            channel = bot.get_channel(channel_id)
                            if channel:
                                try:
                                    import discord
                                    message: discord.Message = await channel.fetch_message(message_id)
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


@aiohttp_jinja2.template("index.html")
async def handle_dashboard(request: web.Request) -> dict[str, Any]:
    """Render the main dashboard page."""
    config: BotConfig = request.app["config"]
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
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str: str = f"{hours:02}:{minutes:02}:{seconds:02}"

    return {
        "stats": stats,
        "uptime": uptime_str,
        "recent_bugs": recent_bugs,
        "version": "v1.1.1",
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
        headers={
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
    await response.prepare(request)

    for line in log_capture.logs:
        await response.write(f"data: {line}\n\n".encode("utf-8"))

    last_log_count: int = len(log_capture.logs)
    while True:
        await asyncio.sleep(1)
        current_logs = list(log_capture.logs)
        if len(current_logs) > last_log_count:
            new_lines = current_logs[last_log_count:]
            for line in new_lines:
                await response.write(f"data: {line}\n\n".encode("utf-8"))
            last_log_count = len(current_logs)

    return response


async def start_web_server(bot: commands.Bot, config: BotConfig) -> web.TCPSite:
    """Initialize and start the aiohttp web server."""
    app: web.Application = web.Application()
    app["bot"] = bot
    app["config"] = config
    
    import os
    template_path = os.path.join(os.path.dirname(__file__), "templates")
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(template_path))

    app.router.add_get("/", handle_dashboard)
    app.router.add_get("/api/stats", handle_stats_api)
    app.router.add_get("/api/logs", handle_log_stream)
    app.router.add_route("*", "/trello-webhook", handle_trello_webhook)
    
    runner: web.AppRunner = web.AppRunner(app)
    await runner.setup()
    site: web.TCPSite = web.TCPSite(runner, config.webhook_host, config.webhook_port)
    await site.start()
    
    log.info("Dashboard server listening on %s:%s", config.webhook_host, config.webhook_port)
    return site

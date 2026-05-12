"""
Main Entry Point
================

Coordinates the startup of the Discord bot and the web dashboard.
"""

from __future__ import annotations

import asyncio
import sys

from bugbot.config import load_config
from bugbot.discord_bot import create_bot, setup_commands
from bugbot.stats import setup_logging
from bugbot.web import start_web_server


async def start_everything() -> None:
    """Initialize and run both the Discord bot and the Web server."""
    # 1. Load Configuration
    config = load_config()
    
    # 2. Setup Logging
    log = setup_logging(config.log_level)
    log.info("Starting Discord Trello Bug Bot (Modular Edition)")
    
    # 3. Initialize Discord Bot
    bot = create_bot(config.command_prefix)
    setup_commands(bot, config)
    
    # 4. Initialize Web Server
    # We don't need to await the site itself, as it runs in the background.
    await start_web_server(bot, config)
    
    # 5. Start Discord Bot (Blocks)
    try:
        await bot.start(config.discord_token)
    finally:
        if not bot.is_closed():
            await bot.close()


def main() -> None:
    """Synchronous entry point."""
    try:
        asyncio.run(start_everything())
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"FATAL ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

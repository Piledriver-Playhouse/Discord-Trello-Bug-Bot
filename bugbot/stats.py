"""
Stats and Logging Module
========================

Handles runtime statistics tracking and log interception for the dashboard.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class BotStats:
    """Track runtime statistics for the dashboard."""
    start_time: datetime = datetime.now(timezone.utc)
    bugs_reported: int = 0
    attachments_synced: int = 0
    threads_created: int = 0
    last_bug_at: datetime | None = None


#: Global stats instance.
stats = BotStats()


class LogCaptureHandler(logging.Handler):
    """Custom logging handler to store the last 100 log lines in memory."""
    def __init__(self, capacity: int = 100) -> None:
        super().__init__()
        self.logs: deque[str] = deque(maxlen=capacity)

    def emit(self, record: logging.LogRecord) -> None:
        msg: str = self.format(record)
        self.logs.append(msg)


#: Global log capture handler instance.
log_capture = LogCaptureHandler()


def setup_logging(level_name: str) -> logging.Logger:
    """Set up global logging and attach the capture handler."""
    level = getattr(logging, level_name.upper(), logging.INFO)
    
    # Configure the root logger
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    )
    
    # Attach our capture handler to the root logger
    log_capture.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logging.getLogger().addHandler(log_capture)
    
    return logging.getLogger("bugbot")

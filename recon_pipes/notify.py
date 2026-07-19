"""Notification backends."""

import json
import urllib.request
from .models import NotifyConfig


def send_notification(config: NotifyConfig, message: str, level: str = "info"):
    """Send notification via webhook (Slack/Discord compatible)."""
    if not config or not config.webhook:
        return

    payload = {"text": message, "content": message}

    try:
        req = urllib.request.Request(
            config.webhook,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass

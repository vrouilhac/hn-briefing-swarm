"""Posting to the swarm's Slack channel through an incoming webhook."""

import os

import requests

SLACK_TEXT_LIMIT = 3900


def post(title: str, body: str) -> None:
    """Posts one message; with DRY_RUN=1 it is printed instead."""
    text = f"*{title}*\n{body}"[:SLACK_TEXT_LIMIT]
    if os.getenv("DRY_RUN") == "1":
        print(f"[dry run] would post to Slack:\n{text}")
        return
    response = requests.post(os.environ["SLACK_WEBHOOK_URL"], json={"text": text}, timeout=15)
    response.raise_for_status()
    print(f"Posted to Slack: {title}")

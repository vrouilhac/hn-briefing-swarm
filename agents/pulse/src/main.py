"""pulse — daily 07:30 health check of the swarm's dependencies (HN API, OpenAI key, Slack webhook). No LLM call.

Silent when everything is fine; posts to Slack and fails the run when a dependency is broken,
so a red square in HollowHost means the other agents are about to fail too.
"""

import os

import requests
from openai import OpenAI

from swarm_core import hn, slack
from swarm_core.job import run


def check_hn() -> str | None:
    try:
        ids = requests.get(f"{hn.FIREBASE}/topstories.json", timeout=hn.TIMEOUT).json()
        return None if ids else "Hacker News API returned no stories"
    except requests.RequestException as e:
        return f"Hacker News API unreachable: {e}"


def check_openai() -> str | None:
    try:
        OpenAI().models.retrieve(os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
        return None
    except Exception as e:
        return f"OpenAI check failed: {type(e).__name__}"


def main() -> None:
    problems = [p for p in (check_hn(), check_openai()) if p]
    if not problems:
        print("All dependencies OK (Hacker News API, OpenAI key and model)")
        return
    slack.post(":rotating_light: HN briefing swarm — dependency check failed", "\n".join(f"• {p}" for p in problems))
    raise RuntimeError("; ".join(problems))


if __name__ == "__main__":
    run("pulse", main)

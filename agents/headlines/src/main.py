"""headlines — weekdays 08:00: the 10 top Hacker News stories, each with one line on why it matters."""

from swarm_core import hn, llm, slack
from swarm_core.job import run

SYSTEM = "You are a tech news editor writing a morning briefing for software engineers."


def main() -> None:
    top = hn.stories("topstories", 12)[:10]
    listing = "\n".join(
        f"{i}. {s['title']} ({s.get('score', 0)} points, {s.get('descendants', 0)} comments) — {s.get('url') or hn.discussion_url(s['id'])}"
        for i, s in enumerate(top, 1)
    )
    body = llm.ask(SYSTEM, (
        "For each story below write exactly one bullet: the title as a Slack link <url|title>, then ' — ' and one short "
        "sentence on why it matters to an engineer. Keep the original order.\n\n" + listing
    ))
    slack.post(":newspaper: Hacker News — this morning's headlines", body)


if __name__ == "__main__":
    run("headlines", main)

"""show-hn-picks — weekdays 17:00: the 3 most interesting Show HN launches of the day, with a one-line pitch each."""

from swarm_core import hn, llm, slack
from swarm_core.job import run

SYSTEM = "You curate new developer tools and side projects for an engineering team."


def main() -> None:
    launches = hn.stories("showstories", 20)
    if not launches:
        print("No Show HN story right now; nothing to pick")
        return
    listing = "\n".join(
        f"- {s['title']} ({s.get('score', 0)} points) — {s.get('url') or hn.discussion_url(s['id'])}" for s in launches
    )
    body = llm.ask(SYSTEM, (
        "From the Show HN launches below, pick the 3 most useful or original for software engineers. For each, write a "
        "bullet: <url|name> — what it does in one sentence, then 'Worth a look because …'.\n\n" + listing
    ), max_tokens=450)
    slack.post(":rocket: Show HN — today's picks", body)


if __name__ == "__main__":
    run("show-hn-picks", main)

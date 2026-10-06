"""weekly-trends — Fridays 18:00: the themes behind the week's most upvoted stories."""

from swarm_core import hn, llm, slack
from swarm_core.job import run

SYSTEM = "You are an analyst spotting trends in what software engineers read and discuss."


def main() -> None:
    best = hn.week_best(days=7, limit=40)
    if not best:
        print("No story above 50 points this week; nothing to analyze")
        return
    listing = "\n".join(f"- {s['title']} ({s['score']} points, {s.get('descendants') or 0} comments)" for s in best)
    body = llm.ask(SYSTEM, (
        "Here are this week's most upvoted Hacker News stories. Group them into 3 to 5 themes. For each theme write a "
        "bold title, one sentence explaining the trend, and the 1-2 most representative story titles.\n\n" + listing
    ), max_tokens=700)
    slack.post(":chart_with_upwards_trend: Hacker News — the week in themes", body)


if __name__ == "__main__":
    run("weekly-trends", main)

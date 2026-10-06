"""deep-dive — weekdays 12:30: reads the most discussed linked article of the top 10 and summarizes it in 5 bullets."""

from swarm_core import hn, llm, slack
from swarm_core.job import run

SYSTEM = "You summarize technical articles for busy engineers, without hype."


def main() -> None:
    candidates = [s for s in hn.stories("topstories", 10) if s.get("url")]
    if not candidates:
        print("No linked story in the top 10 today; nothing to summarize")
        return
    pick = max(candidates, key=lambda s: s.get("descendants") or 0)
    text = hn.article_text(pick["url"])
    source = text if text else "(The article could not be fetched; rely on the title only and say so.)"
    body = llm.ask(SYSTEM, (
        f"Article title: {pick['title']}\nURL: {pick['url']}\n\nArticle text:\n{source}\n\n"
        "Write 5 bullets covering what it is, the key facts and why it matters. End with one line "
        f"'Discussion: <{hn.discussion_url(pick['id'])}|{pick.get('descendants', 0)} comments on HN>'."
    ), max_tokens=500)
    slack.post(f":mag: Deep dive — {pick['title']}", body)


if __name__ == "__main__":
    run("deep-dive", main)

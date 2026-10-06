"""The single LLM call every agent uses."""

import os

from openai import OpenAI


def ask(system: str, prompt: str, max_tokens: int = 700) -> str:
    """Returns the model's answer to one prompt, in the configured digest language."""
    client = OpenAI()
    language = os.getenv("DIGEST_LANGUAGE", "English")
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.4,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": f"{system}\nAlways answer in {language}. Use Slack mrkdwn (*bold*, bullet lines starting with •). Be concise and factual."},
            {"role": "user", "content": prompt},
        ],
    )
    return (response.choices[0].message.content or "").strip()

# hn-briefing-swarm

A small **swarm of five HollowHost AI Jobs** that brief a Slack channel on Hacker News
through the day. Built to exercise HollowHost **Swarms** (grouping, health, activity)
with nothing more than an OpenAI key and a Slack webhook — the Hacker News APIs are public.

| AI Job | When (Europe/Paris) | What it does | LLM |
|---|---|---|---|
| `pulse` | daily 07:30 | Checks the HN API and the OpenAI key/model. Silent when OK; alerts Slack and **fails the run** when a dependency is broken. | no |
| `headlines` | weekdays 08:00 | The 10 top stories, each with one line on why it matters. | yes |
| `deep-dive` | weekdays 12:30 | Reads the most discussed linked article of the top 10, posts a 5-bullet summary. | yes |
| `show-hn-picks` | weekdays 17:00 | The 3 most interesting Show HN launches of the day. | yes |
| `weekly-trends` | Fridays 18:00 | Groups the week's most upvoted stories into 3–5 themes. | yes |

**Why it is a swarm and not one job:** five independent AI Jobs, each on its own cron,
sharing the same source (Hacker News) and the same output (one Slack channel), with no
orchestrator. HollowHost groups them in one swarm whose health is OK when the last run of
every member succeeded.

## Layout

```
pyproject.toml          one package for every job (uv), installs swarm_core
swarm_core/             shared code: hn.py, llm.py, slack.py, job.py
agents/<name>/src/main.py   one entry point per AI Job
scripts/deploy.py       creates/configures/builds the jobs and the swarm through the HollowHost CLI
tests/                  pytest
```

## Configuration

Copy `.env.example` to `.env` and fill it in. Comments must stay on their own line.

| Variable | Kind | Default | Purpose |
|---|---|---|---|
| `OPENAI_API_KEY` | secret | — | OpenAI key (needs billing credits) |
| `SLACK_WEBHOOK_URL` | secret | — | Incoming webhook of the target channel |
| `OPENAI_MODEL` | env | `gpt-4o-mini` | Model used by every agent |
| `DIGEST_LANGUAGE` | env | `English` | Language of the messages |
| `DRY_RUN` | env | `0` | `1` prints the messages instead of posting them |
| `SIMULATE_FAILURE` | env | `0` | `1` makes a job fail on purpose — set it on one job to see the swarm turn **Degraded** |

## Run locally

```bash
uv sync
cp .env.example .env   # then fill it in
uv run python agents/headlines/src/main.py
uv run pytest
```

## Deploy on HollowHost

The repository must be on GitHub (public → `--token-type NONE`, private → set a default
GitHub token in HollowHost Settings and pass `--token-type DEFAULT`).

```bash
# plan (changes nothing)
uv run python scripts/deploy.py --repo <owner>/hn-briefing-swarm
# create the swarm + the 5 AI Jobs, import .env, build
uv run python scripts/deploy.py --repo <owner>/hn-briefing-swarm --apply --deploy
# once every job is DEPLOYED (~3 min): try them all now
uv run python scripts/deploy.py --repo <owner>/hn-briefing-swarm --run-all
# put the crons on
uv run python scripts/deploy.py --repo <owner>/hn-briefing-swarm --activate
```

Each job runs as `python agents/<name>/src/main.py` at the repository root (no sub-path),
Python 3.13, `uv`. A run is **Success** when the script exits 0, **Error** otherwise.

Use `--cli <path>` to target another environment, for example the dev build of the
HollowHost CLI (`packages/cli/dist/hollowhost-dev-bots`). Swarm commands need a CLI built
with Swarm V1.

**Plan limit:** five AI Jobs exceed the Free plan (3). Timeout and memory stay at the
defaults (180 s, 256 MB), so no Options add-on is needed.

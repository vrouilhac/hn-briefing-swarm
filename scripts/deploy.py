"""Creates (or updates) the swarm's five AI Jobs on HollowHost through the CLI, groups them in a swarm, and builds them.

Usage:
  python scripts/deploy.py --repo <owner>/hn-briefing-swarm                     # plan only, changes nothing
  python scripts/deploy.py --repo <owner>/hn-briefing-swarm --apply --deploy    # create/configure + build
  python scripts/deploy.py --repo <owner>/hn-briefing-swarm --activate          # put the crons on
  python scripts/deploy.py --repo <owner>/hn-briefing-swarm --run-all           # run every job once now

Point --cli at another binary to target another environment, e.g. the dev/bots build
(packages/cli/dist/hollowhost-dev-bots) of the HollowHost repo. Swarm support needs a CLI
built from the Swarm V1 branches (`hollowhost swarms --help` must work).
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

# short name, agent folder, cron, description (≤ 200 chars)
JOBS = [
    ("pulse", "pulse", "30 7 * * *", "Daily 07:30 health check of the swarm's dependencies (HN API, OpenAI). Silent when OK, alerts Slack and fails otherwise. No LLM."),
    ("headlines", "headlines", "0 8 * * MON-FRI", "Weekdays 08:00: the 10 top Hacker News stories, each with one line on why it matters, posted to Slack."),
    ("deep-dive", "deep-dive", "30 12 * * MON-FRI", "Weekdays 12:30: reads the most discussed linked article of the HN top 10 and posts a 5-bullet summary."),
    ("show-hn-picks", "show-hn-picks", "0 17 * * MON-FRI", "Weekdays 17:00: the 3 most interesting Show HN launches of the day, with a one-line pitch each."),
    ("weekly-trends", "weekly-trends", "0 18 * * FRI", "Fridays 18:00: groups the week's most upvoted HN stories into 3-5 themes and posts the trends."),
]
SECRETS = "OPENAI_API_KEY,SLACK_WEBHOOK_URL"


class Cli:
    def __init__(self, binary: str):
        self.binary = binary

    def __call__(self, *args: str, parse: bool = True):
        result = subprocess.run([self.binary, *args, "--output", "json"], capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"{self.binary} {' '.join(args[:3])}: {(result.stderr or result.stdout)[:400]}")
        return json.loads(result.stdout) if parse and result.stdout.strip() else {}


def wait_status(cli: Cli, job_id: str, wanted: tuple[str, ...], timeout_s: int) -> str:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        agent = cli("ai-jobs", "get", job_id)["data"]["agent"]
        if agent["status"] in wanted:
            return agent["status"]
        if "ERROR" in agent["status"]:
            raise RuntimeError(f"{job_id}: {agent['status']} — {agent.get('error')}")
        time.sleep(8)
    raise RuntimeError(f"{job_id}: still not {'/'.join(wanted)} after {timeout_s}s")


def ensure_swarm(cli: Cli, name: str, project: str | None, apply: bool) -> str | None:
    swarms = cli("swarms", "list")["data"]["swarms"]
    for s in swarms:
        if s["name"] == name:
            print(f"swarm  {name} ({s['swarmId']}) — exists, {s['memberCount']} AI Jobs, health {s['health']}")
            return s["swarmId"]
    if not apply:
        print(f"swarm  {name} — would be created")
        return None
    args = ["swarms", "create", "--name", name, "--description", "Hacker News briefings posted to Slack through the day."]
    if project:
        args += ["--project", project]
    swarm_id = cli(*args)["data"]["swarm"]["swarmId"]
    print(f"swarm  {name} ({swarm_id}) — created")
    return swarm_id


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True, help="GitHub repository of this code, owner/name")
    p.add_argument("--branch", default=None, help="branch to deploy (default: the repo's default branch)")
    p.add_argument("--cli", default="hollowhost", help="HollowHost CLI binary (default: hollowhost on PATH)")
    p.add_argument("--env-file", default=".env", help="env file imported into every job")
    p.add_argument("--prefix", default="hn-swarm", help="prefix of the AI Job names")
    p.add_argument("--swarm-name", default="hn-briefing", help="swarm grouping the jobs; --no-swarm to skip")
    p.add_argument("--no-swarm", action="store_true", help="do not create or use a swarm")
    p.add_argument("--project", default=None, help="project ID for the jobs and the swarm (optional)")
    p.add_argument("--token-type", default="NONE", choices=["NONE", "DEFAULT"], help="NONE for a public repo, DEFAULT for your profile token")
    p.add_argument("--timezone", default="Europe/Paris", help="timezone of the crons")
    p.add_argument("--apply", action="store_true", help="create/configure the jobs (default: plan only)")
    p.add_argument("--deploy", action="store_true", help="also build them")
    p.add_argument("--activate", action="store_true", help="put and enable every cron")
    p.add_argument("--run-all", action="store_true", help="run every DEPLOYED job once now")
    args = p.parse_args()

    cli = Cli(args.cli)
    env_file = Path(args.env_file)
    if args.apply and not env_file.exists():
        sys.exit(f"Env file not found: {env_file} (copy .env.example and fill it in)")

    full = lambda short: f"{args.prefix} {short}"
    current = {a["name"]: a for a in cli("ai-jobs", "list")["data"]["agents"] if a.get("name")}

    if args.activate or args.run_all:
        for short, _, cron, _ in JOBS:
            job = current.get(full(short))
            if not job:
                print(f"  ! not found: {full(short)} — run --apply --deploy first")
                continue
            if args.activate:
                cli("ai-jobs", "update", job["id"], "--schedule", cron, "--schedule-timezone", args.timezone, "--enable-schedule", parse=False)
                print(f"  ✓ cron on: {full(short):28s} {cron} ({args.timezone})")
            if args.run_all:
                if job["status"] != "DEPLOYED":
                    print(f"  ! skipped (status {job['status']}): {full(short)}")
                    continue
                cli("ai-jobs", "run", job["id"], parse=False)
                print(f"  ▶ run started: {full(short)}")
        return

    swarm_id = None if args.no_swarm else ensure_swarm(cli, args.swarm_name, args.project, args.apply)
    for short, folder, cron, _ in JOBS:
        action = "update" if full(short) in current else "create"
        print(f"{action:6s} {full(short):28s} agents/{folder}/src/main.py   cron '{cron}' (off until --activate)")
    if not args.apply:
        print("\nPlan only. Re-run with --apply --deploy to create and build the jobs.")
        return

    for short, folder, cron, description in JOBS:
        name = full(short)
        print(f"\n=== {name} ===")
        if name in current:
            job_id = current[name]["id"]
            if swarm_id and current[name].get("swarmId") != swarm_id:
                cli("swarms", "add-job", swarm_id, job_id, "--yes", parse=False)
        else:
            create = ["ai-jobs", "create", "--repo", args.repo, "--lang", "python", "--pm", "uv",
                      "--entry-point", f"agents/{folder}/src/main.py", "--token-type", args.token_type]
            if args.branch:
                create += ["--branch", args.branch]
            if args.project:
                create += ["--project", args.project]
            if swarm_id:
                create += ["--swarm", swarm_id]
            created = cli(*create)
            job_id = created.get("agentId") or created["data"]["agent"]["id"]
            print(f"created {job_id}, waiting for validation…")
            wait_status(cli, job_id, ("VALIDATED", "DEPLOYED"), 180)
        cli("ai-jobs", "update", job_id, "--name", name, "--description", description, parse=False)
        cli("ai-jobs", "env", "import", job_id, "--file", str(env_file), "--secrets", SECRETS, parse=False)
        print("configured (name, description, env + secrets)")
        if args.deploy:
            cli("ai-jobs", "deploy", job_id, parse=False)
            print("build started")
    print("\nDone. Builds take ~3 min; then: --run-all to try every job now, --activate to put the crons on.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

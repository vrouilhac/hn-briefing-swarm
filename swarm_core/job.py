"""Job lifecycle shared by every agent: env loading, required variables, failure simulation, exit code."""

import os
import sys
import traceback
from typing import Callable

from dotenv import load_dotenv


def run(name: str, main: Callable[[], None], required: tuple[str, ...] = ("OPENAI_API_KEY", "SLACK_WEBHOOK_URL")) -> None:
    """Runs one agent; HollowHost marks the run Success on exit 0 and Error otherwise."""
    load_dotenv()
    if os.getenv("DRY_RUN") == "1":
        required = tuple(v for v in required if v != "SLACK_WEBHOOK_URL")
    missing = [v for v in required if not os.getenv(v)]
    if missing:
        print(f"[{name}] missing environment variables: {', '.join(missing)}", file=sys.stderr)
        sys.exit(2)
    if os.getenv("SIMULATE_FAILURE") == "1":
        print(f"[{name}] SIMULATE_FAILURE=1: failing on purpose", file=sys.stderr)
        sys.exit(1)
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
    print(f"[{name}] done")

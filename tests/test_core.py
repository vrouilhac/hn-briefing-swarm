"""Unit tests of the pure parts: HTML extraction, Slack dry run, job exit codes."""

import pytest

from swarm_core import slack
from swarm_core.hn import html_to_text
from swarm_core.job import run


def test_html_to_text_keeps_visible_text_only():
    html = "<html><head><style>p{}</style><script>alert(1)</script></head><body><nav>Menu</nav><h1>Title</h1><p>Hello   <b>world</b></p><footer>©</footer></body></html>"
    assert html_to_text(html) == "Title Hello world"


def test_html_to_text_truncates():
    assert len(html_to_text("<p>" + "a " * 10_000 + "</p>", max_chars=100)) == 100


def test_slack_dry_run_prints_instead_of_posting(monkeypatch, capsys):
    monkeypatch.setenv("DRY_RUN", "1")
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    slack.post("Title", "body")
    assert "*Title*\nbody" in capsys.readouterr().out


@pytest.mark.parametrize("env,expected_code", [
    ({"OPENAI_API_KEY": "x", "SLACK_WEBHOOK_URL": "y", "SIMULATE_FAILURE": "1"}, 1),
    ({"SLACK_WEBHOOK_URL": "y"}, 2),
])
def test_job_exit_codes(monkeypatch, env, expected_code):
    for key in ("OPENAI_API_KEY", "SLACK_WEBHOOK_URL", "SIMULATE_FAILURE", "DRY_RUN"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr("swarm_core.job.load_dotenv", lambda: None)
    with pytest.raises(SystemExit) as exit_info:
        run("test", lambda: None)
    assert exit_info.value.code == expected_code


def test_job_failure_inside_main_exits_1(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "y")
    monkeypatch.delenv("SIMULATE_FAILURE", raising=False)
    monkeypatch.setattr("swarm_core.job.load_dotenv", lambda: None)

    def boom():
        raise RuntimeError("boom")

    with pytest.raises(SystemExit) as exit_info:
        run("test", boom)
    assert exit_info.value.code == 1

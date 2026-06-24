"""The runnable demo produces a completed, verified mission report."""

import io

from r2pip_platform.demo import run_demo


def test_demo_runs_and_reports_completed():
    buf = io.StringIO()
    result = run_demo(out=buf)
    output = buf.getvalue()

    assert result.state.status == "completed"
    assert result.chain_valid is True
    assert "Golden Mission MSN-4413" in output
    assert "taint firewall" in output
    assert "staging-tier poison defended" in output
    # ASCII-only so it is safe on any console.
    output.encode("ascii")

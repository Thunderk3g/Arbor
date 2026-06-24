"""Tests for B.4 grounded progress claims."""

from memory_helpers import claim, ledger_entry, task_memory
from r2pip_memory.claims import summary_for_claims_sheet, validate_claims


def test_grounded_claim_passes():
    tm = task_memory(
        tool_ledger=[ledger_entry("led-1", result_status="ok")],
        claims=[claim("ran the search", "led-1")],
    )
    assert validate_claims(tm) == []


def test_missing_evidence_id_is_violation():
    tm = task_memory(claims=[claim("did a thing")])
    violations = validate_claims(tm)
    assert len(violations) == 1
    assert "missing evidence" in violations[0]


def test_unknown_ledger_id_is_violation():
    tm = task_memory(
        tool_ledger=[ledger_entry("led-1")],
        claims=[claim("did a thing", "led-999")],
    )
    violations = validate_claims(tm)
    assert len(violations) == 1
    assert "unknown ledger id" in violations[0]
    assert "led-999" in violations[0]


def test_citing_error_entry_is_violation():
    tm = task_memory(
        tool_ledger=[ledger_entry("led-1", result_status="error")],
        claims=[claim("tests passed", "led-1")],
    )
    violations = validate_claims(tm)
    assert len(violations) == 1
    assert "claim cites failed tool call" in violations[0]


def test_citing_denied_entry_is_violation():
    tm = task_memory(
        tool_ledger=[ledger_entry("led-1", result_status="denied")],
        claims=[claim("deployed it", "led-1")],
    )
    violations = validate_claims(tm)
    assert len(violations) == 1
    assert "claim cites failed tool call" in violations[0]


def test_multiple_violations_collected():
    tm = task_memory(
        tool_ledger=[ledger_entry("led-ok"), ledger_entry("led-err", result_status="error")],
        claims=[
            claim("grounded", "led-ok"),
            claim("uncited"),
            claim("phantom", "led-missing"),
            claim("failed-cite", "led-err"),
        ],
    )
    assert len(validate_claims(tm)) == 3


def test_claims_sheet_contains_tool_and_hash_prefix():
    tm = task_memory(
        task_id="task-7",
        tool_ledger=[
            ledger_entry("led-1", tool="code.search", params_hash="deadbeefcafe1234"),
        ],
        claims=[claim("searched the codebase", "led-1"), claim("untracked work")],
    )
    sheet = summary_for_claims_sheet(tm)
    assert "task-7" in sheet
    assert "searched the codebase" in sheet
    assert "code.search" in sheet
    assert "deadbeef" in sheet  # params_hash prefix
    assert "UNGROUNDED" in sheet  # the uncited claim is flagged for the reviewer

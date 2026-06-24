"""Tests for B.8 lesson store: rationale mandatory, dedup, soft delete."""

import pytest
from pydantic import ValidationError

from r2pip_memory.consolidation import LessonRecord, LessonStore


def lesson(name="l1", summary_line="use retry backoff for flaky api calls",
           body="details", kind="correction", rationale="prevented repeated failures"):
    return LessonRecord(
        name=name, summary_line=summary_line, body=body, kind=kind, rationale=rationale
    )


def test_missing_rationale_rejected_by_pydantic():
    with pytest.raises(ValidationError):
        LessonRecord(
            name="l1",
            summary_line="something",
            body="body",
            kind="correction",
            rationale="",
        )


def test_near_duplicate_updates_in_place():
    store = LessonStore()
    store.add(lesson(name="l1", body="old body"))
    # Jaccard("use retry backoff for flaky api calls",
    #         "use retry backoff for flaky api endpoints") = 6/8 = 0.75 > 0.6
    store.add(
        lesson(
            name="l2",
            summary_line="use retry backoff for flaky api endpoints",
            body="new body",
            rationale="updated after second incident",
        )
    )
    active = store.list_active()
    assert len(active) == 1
    assert active[0].name == "l1"  # original record updated, not replaced
    assert active[0].body == "new body"
    assert active[0].summary_line == "use retry backoff for flaky api endpoints"
    assert active[0].rationale == "updated after second incident"


def test_distinct_lessons_both_kept():
    store = LessonStore()
    store.add(lesson(name="l1"))
    store.add(lesson(name="l2", summary_line="pin dependency versions in sandbox builds"))
    assert len(store.list_active()) == 2


def test_deprecate_excludes_from_active_but_never_deletes():
    store = LessonStore()
    store.add(lesson(name="l1"))
    store.deprecate("l1")
    assert store.list_active() == []
    assert len(store.list_all()) == 1
    assert store.get("l1").deprecated is True


def test_deprecate_unknown_name_raises():
    store = LessonStore()
    with pytest.raises(KeyError):
        store.deprecate("ghost")


def test_confirmed_approach_kind_accepted():
    record = lesson(kind="confirmed_approach")
    assert record.kind == "confirmed_approach"

"""B.8 lesson-file discipline: rationale-mandatory lessons, dedup, soft delete.

Corrections and confirmed approaches are recorded with *why it mattered*; the
store rejects rationale-less writes (pydantic), updates near-duplicate lessons
in place, and deprecates rather than deletes (provenance preserved).
"""

from typing import Literal

from pydantic import BaseModel, Field

_DUPLICATE_JACCARD_THRESHOLD = 0.6


class LessonRecord(BaseModel):
    name: str
    summary_line: str
    body: str
    kind: Literal["correction", "confirmed_approach"]
    rationale: str = Field(min_length=1)  # B.8: writes without a rationale are rejected
    deprecated: bool = False


def _word_set(text: str) -> set[str]:
    return set(text.lower().split())


def _jaccard(a: str, b: str) -> float:
    sa, sb = _word_set(a), _word_set(b)
    if not sa and not sb:
        return 1.0
    union = sa | sb
    if not union:
        return 0.0
    return len(sa & sb) / len(union)


class LessonStore:
    """In-memory lesson store keyed by name, with near-duplicate guard."""

    def __init__(self):
        self._lessons: dict[str, LessonRecord] = {}

    def add(self, lesson: LessonRecord) -> LessonRecord:
        """Add a lesson; near-duplicates update the existing record in place.

        If an existing non-deprecated lesson's summary_line has word-set
        Jaccard similarity > 0.6 with the new lesson's, the existing record is
        updated (keeping its name) instead of a new one being added.
        """
        for name, existing in self._lessons.items():
            if existing.deprecated:
                continue
            if _jaccard(existing.summary_line, lesson.summary_line) > _DUPLICATE_JACCARD_THRESHOLD:
                updated = existing.model_copy(
                    update={
                        "summary_line": lesson.summary_line,
                        "body": lesson.body,
                        "kind": lesson.kind,
                        "rationale": lesson.rationale,
                    }
                )
                self._lessons[name] = updated
                return updated
        self._lessons[lesson.name] = lesson
        return lesson

    def deprecate(self, name: str) -> None:
        """Mark a lesson deprecated; lessons are never deleted."""
        existing = self._lessons.get(name)
        if existing is None:
            raise KeyError(f"no lesson named {name!r}")
        self._lessons[name] = existing.model_copy(update={"deprecated": True})

    def get(self, name: str) -> LessonRecord | None:
        return self._lessons.get(name)

    def list_active(self) -> list[LessonRecord]:
        return [lesson for lesson in self._lessons.values() if not lesson.deprecated]

    def list_all(self) -> list[LessonRecord]:
        return list(self._lessons.values())

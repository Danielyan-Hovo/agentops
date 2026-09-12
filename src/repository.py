from __future__ import annotations

from collections.abc import Iterable
from threading import Lock
from uuid import UUID

from .models import TraceSpan


class DuplicateSpanError(ValueError):
    """Raised when a span ID has already been ingested."""


class TraceRepository:
    """Thread-safe MVP repository; the API contract is storage-independent."""

    def __init__(self) -> None:
        self._spans: dict[UUID, TraceSpan] = {}
        self._lock = Lock()

    def add(self, span: TraceSpan) -> TraceSpan:
        with self._lock:
            if span.span_id in self._spans:
                raise DuplicateSpanError(str(span.span_id))
            self._spans[span.span_id] = span
            return span

    def add_many(self, spans: Iterable[TraceSpan]) -> int:
        added = 0
        for span in spans:
            self.add(span)
            added += 1
        return added

    def get(self, span_id: UUID) -> TraceSpan | None:
        with self._lock:
            return self._spans.get(span_id)

    def by_trace(self, trace_id: UUID) -> list[TraceSpan]:
        with self._lock:
            return [span for span in self._spans.values() if span.trace_id == trace_id]

    def by_project(self, tenant_id: str, project_id: str, limit: int = 100) -> list[TraceSpan]:
        with self._lock:
            matches = [
                span
                for span in self._spans.values()
                if span.tenant_id == tenant_id and span.project_id == project_id
            ]
            return matches[-limit:]

    def count(self) -> int:
        with self._lock:
            return len(self._spans)

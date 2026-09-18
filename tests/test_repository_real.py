from __future__ import annotations

from src.repository import TraceRepository, DuplicateSpanError
from src.models import TraceSpan, SpanKind, SpanStatus
from uuid import UUID


def test_repository_add_and_get():
    repo = TraceRepository()
    span = TraceSpan(
        trace_id=UUID("12345678-1234-5678-1234-567812345678"),
        span_id=UUID("87654321-4321-8765-4321-876543210987"),
        tenant_id="t1",
        project_id="p1",
        kind=SpanKind.AGENT_RUN,
        name="test",
    )
    result = repo.add(span)
    assert result.span_id == span.span_id
    retrieved = repo.get(span.span_id)
    assert retrieved is not None
    assert retrieved.name == "test"


def test_repository_duplicate_raises():
    repo = TraceRepository()
    span = TraceSpan(
        trace_id=UUID("12345678-1234-5678-1234-567812345678"),
        span_id=UUID("87654321-4321-8765-4321-876543210987"),
        tenant_id="t1",
        project_id="p1",
        kind=SpanKind.AGENT_RUN,
        name="dup",
    )
    repo.add(span)
    try:
        repo.add(span)
        assert False, "Should raise DuplicateSpanError"
    except DuplicateSpanError:
        pass


def test_repository_by_project():
    repo = TraceRepository()
    for i in range(3):
        span = TraceSpan(
            trace_id=UUID("12345678-1234-5678-1234-567812345678"),
            span_id=UUID(f"00000000-0000-0000-0000-{i:012d}"),
            tenant_id="t1",
            project_id="p1",
            kind=SpanKind.AGENT_RUN,
            name=f"span_{i}",
        )
        repo.add(span)
    results = repo.by_project("t1", "p1", limit=2)
    assert len(results) == 2


def test_repository_count():
    repo = TraceRepository()
    assert repo.count() == 0
    span = TraceSpan(
        trace_id=UUID("12345678-1234-5678-1234-567812345678"),
        span_id=UUID("87654321-4321-8765-4321-876543210987"),
        tenant_id="t1",
        project_id="p1",
        kind=SpanKind.AGENT_RUN,
        name="count_test",
    )
    repo.add(span)
    assert repo.count() == 1

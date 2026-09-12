from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable
from uuid import UUID

from .models import SpanKind, SpanStatus, TraceSpan


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    span_id: UUID | None = None
    severity: str = "error"


@dataclass(frozen=True)
class AnomalyRule:
    repeated_tool_limit: int = 3
    latency_limit_ms: float = 30_000
    token_limit: int = 100_000


def validate_trace(spans: Iterable[TraceSpan]) -> list[ValidationIssue]:
    items = list(spans)
    issues: list[ValidationIssue] = []
    if not items:
        return [ValidationIssue("empty_trace", "trace contains no spans")]

    trace_ids = {span.trace_id for span in items}
    if len(trace_ids) != 1:
        issues.append(ValidationIssue("mixed_trace", "all spans must belong to one trace"))

    known = {span.span_id for span in items}
    children: dict[UUID, list[UUID]] = defaultdict(list)
    for span in items:
        if span.parent_span_id is not None:
            if span.parent_span_id == span.span_id:
                issues.append(ValidationIssue("self_parent", "span cannot parent itself", span.span_id))
            elif span.parent_span_id not in known:
                issues.append(ValidationIssue("missing_parent", "parent span is missing", span.span_id))
            else:
                children[span.parent_span_id].append(span.span_id)
        if span.ended_at and span.ended_at < span.started_at:
            issues.append(ValidationIssue("invalid_time", "span ended before it started", span.span_id))

    if _has_cycle(children):
        issues.append(ValidationIssue("cycle", "span parent graph contains a cycle"))
    return issues


def detect_anomalies(spans: Iterable[TraceSpan], rule: AnomalyRule = AnomalyRule()) -> list[ValidationIssue]:
    items = list(spans)
    issues: list[ValidationIssue] = []
    tool_counts: dict[str, int] = defaultdict(int)
    for span in items:
        if span.kind == SpanKind.TOOL:
            tool_counts[span.name] += 1
            if tool_counts[span.name] > rule.repeated_tool_limit:
                issues.append(ValidationIssue("tool_loop", f"tool repeated: {span.name}", span.span_id, "warning"))
        duration = span.duration_ms
        if duration is not None and duration > rule.latency_limit_ms:
            issues.append(ValidationIssue("latency_spike", "span exceeded latency limit", span.span_id, "warning"))
        tokens = _token_total(span)
        if tokens > rule.token_limit:
            issues.append(ValidationIssue("token_spike", "span exceeded token limit", span.span_id, "warning"))
        if span.status == SpanStatus.ERROR and span.kind == SpanKind.TOOL:
            issues.append(ValidationIssue("tool_error", "tool call failed", span.span_id, "warning"))
    return issues


def _token_total(span: TraceSpan) -> int:
    return sum(
        int(span.attributes.get(key, 0) or 0)
        for key in ("gen_ai.usage.input_tokens", "gen_ai.usage.output_tokens")
    )


def _has_cycle(children: dict[UUID, list[UUID]]) -> bool:
    visiting: set[UUID] = set()
    visited: set[UUID] = set()

    def visit(node: UUID) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        if any(visit(child) for child in children.get(node, [])):
            return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in list(children))

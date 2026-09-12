from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from threading import Lock

from .models import SpanKind, SpanStatus, TraceSpan


@dataclass(frozen=True)
class MetricSnapshot:
    spans_total: int
    errors_total: int
    tool_calls_total: int
    llm_calls_total: int
    tokens_total: int


class TraceMetrics:
    """Low-cardinality in-process metrics; export adapters can consume snapshots."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._spans_total = 0
        self._errors_total = 0
        self._tool_calls_total = 0
        self._llm_calls_total = 0
        self._tokens_total = 0
        self._status = Counter()

    def observe(self, span: TraceSpan) -> None:
        with self._lock:
            self._spans_total += 1
            self._status[span.status.value] += 1
            if span.status == SpanStatus.ERROR:
                self._errors_total += 1
            if span.kind == SpanKind.TOOL:
                self._tool_calls_total += 1
            if span.kind == SpanKind.LLM:
                self._llm_calls_total += 1
                self._tokens_total += sum(
                    int(span.attributes.get(key, 0) or 0)
                    for key in ("gen_ai.usage.input_tokens", "gen_ai.usage.output_tokens")
                )

    def observe_many(self, spans: list[TraceSpan]) -> None:
        for span in spans:
            self.observe(span)

    def snapshot(self) -> MetricSnapshot:
        with self._lock:
            return MetricSnapshot(
                spans_total=self._spans_total,
                errors_total=self._errors_total,
                tool_calls_total=self._tool_calls_total,
                llm_calls_total=self._llm_calls_total,
                tokens_total=self._tokens_total,
            )

    def prometheus(self) -> str:
        snapshot = self.snapshot()
        lines = [
            "# TYPE agentops_spans_total counter",
            f"agentops_spans_total {snapshot.spans_total}",
            "# TYPE agentops_errors_total counter",
            f"agentops_errors_total {snapshot.errors_total}",
            "# TYPE agentops_tool_calls_total counter",
            f"agentops_tool_calls_total {snapshot.tool_calls_total}",
            "# TYPE agentops_llm_calls_total counter",
            f"agentops_llm_calls_total {snapshot.llm_calls_total}",
            "# TYPE agentops_tokens_total counter",
            f"agentops_tokens_total {snapshot.tokens_total}",
        ]
        return "\n".join(lines) + "\n"

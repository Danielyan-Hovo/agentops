from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator
from uuid import UUID, uuid4

from .models import SpanKind, SpanStatus, TraceSpan
from .redaction import RedactionPolicy, redact_value


class AgentTracer:
    """Small framework-neutral tracer that emits canonical AgentOps spans."""

    def __init__(
        self,
        tenant_id: str,
        project_id: str,
        redaction: RedactionPolicy = RedactionPolicy(),
    ) -> None:
        self.tenant_id = tenant_id
        self.project_id = project_id
        self.redaction = redaction
        self.spans: list[TraceSpan] = []
        self._active: list[TraceSpan] = []

    @property
    def trace_id(self) -> UUID | None:
        return self.spans[0].trace_id if self.spans else None

    def start_span(
        self,
        kind: SpanKind,
        name: str,
        *,
        attributes: dict[str, Any] | None = None,
    ) -> TraceSpan:
        parent = self._active[-1] if self._active else None
        span = TraceSpan(
            trace_id=parent.trace_id if parent else uuid4(),
            parent_span_id=parent.span_id if parent else None,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            kind=kind,
            name=name,
            attributes=redact_value(attributes or {}, self.redaction),
        )
        self.spans.append(span)
        return span

    @contextmanager
    def span(
        self,
        kind: SpanKind,
        name: str,
        *,
        attributes: dict[str, Any] | None = None,
    ) -> Iterator[TraceSpan]:
        current = self.start_span(kind, name, attributes=attributes)
        self._active.append(current)
        try:
            yield current
        except Exception as exc:
            current.add_event("exception", type=type(exc).__name__, message=str(exc))
            current.finish(SpanStatus.ERROR)
            raise
        else:
            current.finish(SpanStatus.OK)
        finally:
            self._active.pop()

    def record_llm_call(
        self,
        model: str,
        *,
        provider: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        attributes: dict[str, Any] | None = None,
    ) -> TraceSpan:
        data = {
            "gen_ai.system": provider,
            "gen_ai.request.model": model,
            "gen_ai.usage.input_tokens": input_tokens,
            "gen_ai.usage.output_tokens": output_tokens,
            **(attributes or {}),
        }
        return self.start_span(SpanKind.LLM, "llm.call", attributes=data).finish()

    def record_tool_call(
        self,
        tool_name: str,
        *,
        success: bool,
        attributes: dict[str, Any] | None = None,
    ) -> TraceSpan:
        data = {"tool.name": tool_name, "tool.success": success, **(attributes or {})}
        status = SpanStatus.OK if success else SpanStatus.ERROR
        return self.start_span(SpanKind.TOOL, tool_name, attributes=data).finish(status)

    def export(self) -> list[dict[str, Any]]:
        return [span.model_dump(mode="json") for span in self.spans]

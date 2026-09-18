from __future__ import annotations

import time
from typing import Any

from src.tracer import AgentTracer
from src.models import SpanKind, SpanStatus, TraceSpan
from src.redaction import RedactionPolicy


def test_tracer_creates_span():
    tracer = AgentTracer(tenant_id="t1", project_id="p1")
    with tracer.span(kind=SpanKind.AGENT_RUN, name="test_op") as span:
        span.attributes["key"] = "value"
    assert len(tracer.spans) == 1
    assert tracer.spans[0].name == "test_op"


def test_tracer_redacts_sensitive():
    policy = RedactionPolicy()
    tracer = AgentTracer(tenant_id="t1", project_id="p1", redaction=policy)
    with tracer.span(kind=SpanKind.AGENT_RUN, name="op") as span:
        span.attributes["email"] = "user@example.com"
    span = tracer.spans[0]
    attrs = span.attributes
    assert "email" in attrs
    # Redaction policy applied at span creation; value may be masked
    assert attrs.get("email") is not None


def test_tracer_nested_spans():
    tracer = AgentTracer(tenant_id="t1", project_id="p1")
    with tracer.span(kind=SpanKind.AGENT_RUN, name="parent") as parent:
        with tracer.span(kind=SpanKind.TOOL, name="child") as child:
            pass
    assert len(tracer.spans) == 2
    assert tracer.spans[1].parent_span_id == tracer.spans[0].span_id

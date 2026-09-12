import pytest

from src.models import SpanKind, SpanStatus
from src.redaction import RedactionPolicy, redact_value
from src.tracer import AgentTracer


def test_root_and_child_spans_share_trace_id():
    tracer = AgentTracer("tenant-a", "project-a")
    with tracer.span(SpanKind.AGENT_RUN, "run") as root:
        with tracer.span(SpanKind.AGENT_STEP, "step") as child:
            assert child.parent_span_id == root.span_id
            assert child.trace_id == root.trace_id
    assert root.status == SpanStatus.OK
    assert child.status == SpanStatus.OK
    assert len(tracer.export()) == 2


def test_exception_marks_span_as_error():
    tracer = AgentTracer("tenant-a", "project-a")
    with pytest.raises(ValueError):
        with tracer.span(SpanKind.TOOL, "database.lookup"):
            raise ValueError("boom")
    assert tracer.spans[0].status == SpanStatus.ERROR
    assert tracer.spans[0].events[0].name == "exception"


def test_llm_and_tool_helpers_emit_canonical_attributes():
    tracer = AgentTracer("tenant-a", "project-a")
    llm = tracer.record_llm_call("model-a", provider="provider-a", input_tokens=4, output_tokens=2)
    tool = tracer.record_tool_call("search", success=False)
    assert llm.kind == SpanKind.LLM
    assert llm.attributes["gen_ai.usage.input_tokens"] == 4
    assert tool.status == SpanStatus.ERROR
    assert tool.attributes["tool.name"] == "search"


def test_redaction_handles_nested_values_and_credentials():
    value = {"user": "person@example.com", "nested": ["api_key=secret-value"]}
    result = redact_value(value)
    assert "person@example.com" not in str(result)
    assert "secret-value" not in str(result)


def test_redaction_can_be_disabled_but_length_is_bounded():
    policy = RedactionPolicy(enabled=False, max_string_length=5)
    assert redact_value("abcdef", policy) == "abcde"

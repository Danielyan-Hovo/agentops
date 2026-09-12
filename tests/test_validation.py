from src.metrics import TraceMetrics
from src.models import SpanKind, SpanStatus, TraceSpan
from src.validation import AnomalyRule, detect_anomalies, validate_trace


def span(kind, name, parent=None, **attributes):
    return TraceSpan(
        tenant_id="tenant-a",
        project_id="project-a",
        kind=kind,
        name=name,
        parent_span_id=parent,
        attributes=attributes,
    ).finish()


def test_validate_trace_accepts_parent_graph():
    root = span(SpanKind.AGENT_RUN, "run")
    child = span(SpanKind.TOOL, "search", root.span_id)
    child.trace_id = root.trace_id
    assert validate_trace([root, child]) == []


def test_validate_trace_reports_missing_parent():
    child = span(SpanKind.TOOL, "search")
    child.parent_span_id = root_id = child.span_id
    child.parent_span_id = root_id
    issues = validate_trace([child])
    assert any(issue.code == "self_parent" for issue in issues)


def test_detect_anomalies_reports_repeated_tools_and_tokens():
    spans = [span(SpanKind.TOOL, "search") for _ in range(4)]
    spans.append(span(SpanKind.LLM, "llm.call", **{"gen_ai.usage.input_tokens": 80, "gen_ai.usage.output_tokens": 30}))
    issues = detect_anomalies(spans, AnomalyRule(repeated_tool_limit=3, token_limit=100))
    assert any(issue.code == "tool_loop" for issue in issues)
    assert any(issue.code == "token_spike" for issue in issues)


def test_metrics_snapshot_is_low_cardinality():
    metrics = TraceMetrics()
    error = span(SpanKind.TOOL, "search").finish(SpanStatus.ERROR)
    llm = span(SpanKind.LLM, "llm.call", **{"gen_ai.usage.input_tokens": 3})
    metrics.observe_many([error, llm])
    snapshot = metrics.snapshot()
    assert snapshot.spans_total == 2
    assert snapshot.errors_total == 1
    assert snapshot.tokens_total == 3
    assert "agentops_spans_total 2" in metrics.prometheus()

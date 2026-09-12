from uuid import uuid4

from fastapi.testclient import TestClient

from src.api import create_app
from src.models import SpanKind, TraceSpan
from src.repository import TraceRepository


def make_span(trace_id=None, name="run"):
    return TraceSpan(
        trace_id=trace_id or uuid4(),
        tenant_id="tenant-a",
        project_id="project-a",
        kind=SpanKind.AGENT_RUN,
        name=name,
    )


def test_health_and_readiness():
    client = TestClient(create_app(TraceRepository()))
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/readyz").json() == {"status": "ready", "spans": 0}


def test_batch_ingestion_and_trace_query():
    trace_id = uuid4()
    first = make_span(trace_id, "run")
    second = make_span(trace_id, "step")
    client = TestClient(create_app(TraceRepository()))

    response = client.post("/v1/spans", json={"spans": [first.model_dump(mode="json"), second.model_dump(mode="json")]})
    assert response.status_code == 202
    assert response.json() == {"accepted": 2, "rejected": 0}
    queried = client.get(f"/v1/traces/{trace_id}")
    assert queried.status_code == 200
    assert {item["name"] for item in queried.json()} == {"run", "step"}


def test_duplicate_span_is_rejected():
    span = make_span()
    client = TestClient(create_app(TraceRepository()))
    payload = {"spans": [span.model_dump(mode="json")]}
    assert client.post("/v1/spans", json=payload).status_code == 202
    assert client.post("/v1/spans", json=payload).status_code == 409


def test_missing_trace_is_not_found():
    client = TestClient(create_app(TraceRepository()))
    assert client.get(f"/v1/traces/{uuid4()}").status_code == 404

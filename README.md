# AgentOps — Production Agent Observability & Verification Platform

**Author:** danielyan-hovo  
**Category:** Python / FastAPI / AI Agent Evaluation / DevOps  
**Status:** Active Development

## Overview
Self-hostable open-source platform for monitoring, tracing, and verifying AI agent behavior in production.

## Key Technologies
- FastAPI, PostgreSQL, OpenTelemetry, PromQL, Docker, K3s, RAG, LLM Integration

## Project Structure
- `/src` — FastAPI backend
- `/dashboard` — Grafana templates
- `/docs` — ADRs
- `/migrations` — PostgreSQL schema
- `/tests` — Unit and API tests
- `/k8s` — K3s deployment manifests

## Implemented Core

- Canonical trace/span model with parent-child correlation
- Privacy-first redaction for credentials and email values
- Framework-neutral `AgentTracer` context manager
- Batch ingestion and trace query API
- Deterministic trace validation and anomaly rules
- Low-cardinality metrics snapshots and Prometheus text output
- PostgreSQL storage migration and typed environment settings

## Local Development

```bash
python -m venv .venv
python -m pip install -r requirements.txt
pytest -q
python -m uvicorn src.api:app --reload
```

Health endpoints:

- `GET /healthz`
- `GET /readyz`
- `POST /v1/spans`
- `GET /v1/traces/{trace_id}`
- `GET /v1/spans?tenant_id=...&project_id=...`

## K3s Development

```bash
docker build -t agentops:dev .
kubectl apply -f k8s/deployment.yaml
kubectl -n agentops port-forward svc/agentops-api 8000:80
```

The deployment intentionally disables raw content capture by default. Database credentials must be provided through the `agentops-secrets` Kubernetes Secret.

## Architecture

```text
Agent SDK / framework adapter
			  |
			  v
	 OpenTelemetry-compatible envelope
			  |
			  v
	   FastAPI ingestion API
		  |             |
		  v             v
   TraceRepository   validation/anomaly rules
		  |             |
		  v             v
 PostgreSQL storage  Prometheus-compatible metrics
```

The current repository keeps the storage contract independent from the API. The development repository is in-memory, while `migrations/001_trace_storage.sql` defines the PostgreSQL target schema. This keeps tests fast while preserving the production boundary.

## Canonical Span Types

AgentOps uses a small provider-neutral vocabulary:

| Kind | Purpose |
| --- | --- |
| `agent.run` | Complete user-visible workflow |
| `agent.step` | Planner, executor, evaluator, or handoff |
| `gen_ai.chat` | Model invocation and token usage |
| `tool.call` | External tool execution |
| `retrieval` | Search or document retrieval |
| `evaluation` | Quality or policy evaluation |

Every span contains a `trace_id`, `span_id`, optional `parent_span_id`, tenant/project identity, status, timestamps, attributes, events, and schema version.

## Python SDK Example

```python
from src.models import SpanKind
from src.tracer import AgentTracer

tracer = AgentTracer(tenant_id="demo", project_id="support-agent")

with tracer.span(SpanKind.AGENT_RUN, "support.request") as run:
	with tracer.span(SpanKind.AGENT_STEP, "retrieve.context"):
		tracer.record_tool_call("knowledge.search", success=True)
	tracer.record_llm_call(
		"example-model",
		provider="example-provider",
		input_tokens=120,
		output_tokens=42,
	)

payload = tracer.export()
```

The tracer keeps raw content out of attributes by default. If attributes contain credentials, tokens, or email addresses, the redaction policy replaces them before the span is exported.

## Ingestion API

Submit one bounded batch of canonical spans:

```bash
curl -X POST http://localhost:8000/v1/spans \
  -H "content-type: application/json" \
  -d '{"spans":[{"tenant_id":"demo","project_id":"support-agent","kind":"agent.run","name":"support.request","status":"ok","attributes":{},"events":[]}]}'
```

Successful ingestion returns `202`:

```json
{"accepted": 1, "rejected": 0}
```

The same `span_id` cannot be inserted twice. A duplicate returns `409`, allowing callers to retry safely without silently creating duplicate telemetry.

## Query API

Retrieve a trace:

```bash
curl http://localhost:8000/v1/traces/<trace-id>
```

List recent spans for a tenant and project:

```bash
curl "http://localhost:8000/v1/spans?tenant_id=demo&project_id=support-agent&limit=100"
```

The repository and API enforce tenant/project filtering at the query boundary. Future PostgreSQL adapters must preserve that contract with SQL predicates and, where appropriate, row-level security.

## Privacy and Security Defaults

- Raw prompts, tool arguments, retrieved documents, and model outputs are not captured automatically.
- Credential-like values and email addresses are redacted recursively.
- Content capture should be explicitly enabled per environment and policy.
- Prometheus labels remain low-cardinality; trace IDs and user identifiers must not become labels.
- Kubernetes credentials are supplied through Secrets, never through committed manifests.
- The PostgreSQL migration stores flexible attributes in JSONB while indexing tenant, project, trace, parent, and time fields.

## Deterministic Analysis

The first analysis layer intentionally avoids an LLM dependency. It can detect:

- missing or self-referencing parents;
- mixed trace IDs and invalid timestamps;
- cycles in the parent graph;
- repeated tool calls that suggest a loop;
- latency spikes;
- token spikes;
- failed tool calls.

Each issue has a stable code, message, optional span ID, and severity. An LLM-based explanation layer can be added later without changing the deterministic gate.

## Metrics

The in-process metrics adapter currently exports:

- `agentops_spans_total`;
- `agentops_errors_total`;
- `agentops_tool_calls_total`;
- `agentops_llm_calls_total`;
- `agentops_tokens_total`.

These counters are intentionally aggregate. Provider, framework, and project dimensions should be bounded before adding them to a Prometheus exporter.

## Test and Quality Commands

```bash
pytest -q
python -m compileall -q src
```

The suite covers tracing lifecycle, exception status, redaction, API ingestion, duplicate handling, query behavior, graph validation, anomaly rules, metrics, and settings.

## Configuration

Settings use the `AGENTOPS_` environment prefix:

| Variable | Default | Meaning |
| --- | --- | --- |
| `AGENTOPS_ENVIRONMENT` | `development` | Runtime environment |
| `AGENTOPS_DATABASE_URL` | local PostgreSQL URL | Persistence connection |
| `AGENTOPS_MAX_BATCH_SIZE` | `1000` | Maximum spans per request |
| `AGENTOPS_RETENTION_DAYS` | `30` | Planned retention window |
| `AGENTOPS_CAPTURE_CONTENT` | `false` | Opt-in raw content capture |
| `AGENTOPS_OTLP_ENDPOINT` | unset | Optional collector endpoint |

## Deployment Notes

The K3s manifest is a deployment contract, not a complete production installation. Before production use, add:

1. a sealed or external Secret for the database URL;
2. a real PostgreSQL instance and migration job;
3. NetworkPolicy rules for API, collector, and database traffic;
4. TLS ingress and authentication;
5. an OpenTelemetry Collector with bounded queues and a dead-letter strategy;
6. backup, retention, and deletion procedures;
7. dashboard and alert rules for ingestion lag, errors, and database saturation.

## Current Roadmap

- PostgreSQL repository adapter and migration runner
- OpenTelemetry Collector ingestion
- Framework adapters for custom agents and LangChain
- Trace retention and deletion jobs
- Evaluation datasets, replay, and human annotations
- Grafana dashboards and alert delivery
- Keycloak or OIDC tenant authorization

## Troubleshooting

If the API does not start, verify the virtual environment and dependencies first:

```bash
python -m pip install -r requirements.txt
python -c "from src.api import app; print(app.title)"
```

If a trace query returns `404`, confirm that all spans use the same `trace_id` and that the ingestion response returned `accepted` greater than zero. If a duplicate returns `409`, reuse the original span ID intentionally or create a new span ID for a new attempt.

If K3s readiness remains false, inspect the pod logs and confirm the `agentops-secrets` Secret exists in the `agentops` namespace. The current readiness endpoint checks the in-process repository count; the PostgreSQL adapter will add database connectivity checks later.

## Contributing

Keep new instrumentation framework-neutral. Add a canonical span mapping before adding a framework-specific adapter. Every new attribute must have a bounded-cardinality decision and a privacy review.

Pull requests should include:

- focused unit or API tests;
- a note about redaction and tenant boundaries;
- updated migration notes for storage changes;
- the result of `pytest -q` and `python -m compileall -q src`;
- a short operational note when metrics, retention, or deployment behavior changes.

The project favors deterministic, inspectable analysis first. AI-generated explanations belong after the evidence-producing path and must never hide validation failures.

Use feature branches for changes and keep secrets outside Git.

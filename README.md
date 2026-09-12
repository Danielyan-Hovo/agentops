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

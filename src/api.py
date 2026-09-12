from __future__ import annotations

from uuid import UUID

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from .models import TraceSpan
from .repository import DuplicateSpanError, TraceRepository


class BatchIngestRequest(BaseModel):
    spans: list[TraceSpan] = Field(min_length=1, max_length=1000)


class IngestResponse(BaseModel):
    accepted: int
    rejected: int = 0


def create_app(repository: TraceRepository | None = None) -> FastAPI:
    store = repository or TraceRepository()
    app = FastAPI(title="AgentOps Ingestion API", version="0.1.0")
    app.state.repository = store

    @app.get("/healthz")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    async def ready() -> dict[str, int | str]:
        return {"status": "ready", "spans": store.count()}

    @app.post("/v1/spans", response_model=IngestResponse, status_code=202)
    async def ingest(request: BatchIngestRequest) -> IngestResponse:
        try:
            accepted = store.add_many(request.spans)
        except DuplicateSpanError as exc:
            raise HTTPException(status_code=409, detail=f"duplicate span: {exc}") from exc
        return IngestResponse(accepted=accepted)

    @app.get("/v1/traces/{trace_id}", response_model=list[TraceSpan])
    async def get_trace(trace_id: UUID) -> list[TraceSpan]:
        spans = store.by_trace(trace_id)
        if not spans:
            raise HTTPException(status_code=404, detail="trace not found")
        return spans

    @app.get("/v1/spans", response_model=list[TraceSpan])
    async def list_spans(
        tenant_id: str = Query(min_length=1, max_length=128),
        project_id: str = Query(min_length=1, max_length=128),
        limit: int = Query(default=100, ge=1, le=1000),
    ) -> list[TraceSpan]:
        return store.by_project(tenant_id, project_id, limit)

    return app


app = create_app()

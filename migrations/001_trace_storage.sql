CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS trace_spans (
    span_id UUID PRIMARY KEY,
    trace_id UUID NOT NULL,
    parent_span_id UUID NULL REFERENCES trace_spans(span_id),
    tenant_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'unset',
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ NULL,
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    events JSONB NOT NULL DEFAULT '[]'::jsonb,
    schema_version TEXT NOT NULL DEFAULT '1.0',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS trace_spans_trace_id_idx
    ON trace_spans (trace_id, started_at);
CREATE INDEX IF NOT EXISTS trace_spans_project_idx
    ON trace_spans (tenant_id, project_id, started_at DESC);
CREATE INDEX IF NOT EXISTS trace_spans_parent_idx
    ON trace_spans (parent_span_id);
CREATE INDEX IF NOT EXISTS trace_spans_attributes_idx
    ON trace_spans USING GIN (attributes jsonb_path_ops);

CREATE TABLE IF NOT EXISTS trace_anomalies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id UUID NOT NULL,
    span_id UUID NULL REFERENCES trace_spans(span_id),
    tenant_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    code TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    fingerprint TEXT NOT NULL,
    UNIQUE (trace_id, span_id, code, fingerprint)
);

CREATE INDEX IF NOT EXISTS trace_anomalies_project_idx
    ON trace_anomalies (tenant_id, project_id, detected_at DESC);

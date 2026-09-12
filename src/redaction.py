from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


_SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,}]+"),
    re.compile(r"\b(?:ghp|github_pat|sk)-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\b[A-Za-z0-9+/]{32,}={0,2}\b"),
)
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")


@dataclass(frozen=True)
class RedactionPolicy:
    enabled: bool = True
    replacement: str = "[REDACTED]"
    max_string_length: int = 4096
    hash_content: bool = False


def redact_text(value: str, policy: RedactionPolicy = RedactionPolicy()) -> str:
    if not policy.enabled:
        return value[: policy.max_string_length]
    redacted = value
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub(policy.replacement, redacted)
    redacted = _EMAIL.sub(policy.replacement, redacted)
    return redacted[: policy.max_string_length]


def redact_value(value: Any, policy: RedactionPolicy = RedactionPolicy()) -> Any:
    if isinstance(value, str):
        return redact_text(value, policy)
    if isinstance(value, list):
        return [redact_value(item, policy) for item in value]
    if isinstance(value, tuple):
        return [redact_value(item, policy) for item in value]
    if isinstance(value, dict):
        return {str(key): redact_value(item, policy) for key, item in value.items()}
    return value

"""Shared helpers for the health domain tests."""

import uuid
from typing import Any

METRICS = "/v1/health-metrics"


def create(client: Any, owner: dict[str, str], **fields: Any) -> Any:
    body = {
        "source": "scale",
        "metric_type": "weight",
        "value": 72.5,
        "recorded_at": "2026-10-10T06:30:00+00:00",
    }
    return client.post(METRICS, headers=owner, json={**body, **fields})


def another_workspace(harness: Any, platform: Any) -> dict[str, str]:
    """Headers of a second owner in a different workspace, with every permission."""
    actor, workspace = uuid.uuid4(), uuid.uuid4()
    platform.grants[actor] = set(harness.cell.permissions())
    headers: dict[str, str] = harness.token(actor, workspace)
    return headers

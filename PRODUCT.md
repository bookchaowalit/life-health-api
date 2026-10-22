# Product

<!-- impeccable:product-schema 1 -->

## Platform

api

## Users

- The Solo Empire owner, through the cell's own MCP server (`health-mcp`, tools
  `health.health-metric.list|get|create|update|delete`) and the hosted tool hub
  (`platform-mcp-remote-worker`, which lists this cell's origin).
- Local owner tooling that reads cells through the registry client: `ops-toolkit`
  (`infra/scripts/utils/cell_store.py`) and `mcp-aggregator` (`src/cell-store.ts`, `EMPIRE_HEALTH_API`).
- Automations with an `empire-platform` token (for example `owner-mcp`), within the permissions
  `health.health-metric:read|write|delete`.
- No web page reads this cell: `life-dashboard-web` has no health module. Devices or apps that
  would write readings are [ต้องยืนยัน].

## Product Purpose

A single time-stamped log of health readings (weight, heart rate, sleep and the like): each reading
has a source, a metric type, a numeric value, an optional unit and the time it was recorded. It
keeps the raw readings in one place so that later analysis does not depend on the device or app
they came from.

Success: each reading the owner chooses to keep is stored once with its source and time, can be
corrected, and is visible only inside the owner's workspace.

## Positioning

One capability, one service: its own API (Railway), its own database (Neon) with row-level
security per workspace, and authorization, executions and audit through `empire-platform`. It is
workspace-scoped, so the same service can serve other tenants without code changes.

## Operating Context

- Production: `https://health-api-production-c72f.up.railway.app` (`/health`), deployed by merging
  to `main` after CI.
- The cell was created empty on 2026-10-11: the old SQLite `health_metrics` table held no rows, so
  nothing was imported. Imports through the API keep the old id in `legacy_id`.
- Monitored by `platform-uptime-worker` (`health-api`); errors go to Sentry when `SENTRY_DSN` is set.
- This cell publishes no graph events (`cell.yaml` has no `graph:`).

## Capabilities and Constraints

- `/v1/health-metrics`: list, stats, get, get-by-legacy-id, create (with `Idempotency-Key`), patch
  (with `expected_version`), delete.
- Rules tested:
  - `source`, `metric_type`, `value` and `recorded_at` are required; `source` and `metric_type`
    cannot be empty; none of the four can be cleared by a patch (422 `invalid_value`).
  - `value` is a number (decimals, zero and negatives are accepted); `recorded_at` is a timestamp.
  - `source`, `metric_type`, `unit` and `metadata` are free text: there is no list of metric types
    and `metadata` is text, not JSON.
  - Nothing is unique: two identical readings are both stored.
  - The cell declares no filters: a list accepts only paging (`limit`, `offset`, `after_id`,
    `order`), `id`, `legacy_id`, `updated_since` and `null`, and any other field is refused with 422
    `unknown_filter`. `stats` therefore refuses every `group_by` (422).
  - Another workspace sees none of an owner's readings (404 on read, patch and delete, empty list).
- A `NaN` or `Infinity` value is currently accepted and read back as `null` (known gap in the
  shared service code, covered by an expected-failure test).
- Out of scope: units conversion, ranges or alerts per metric type, aggregation (daily averages,
  trends) and importing from devices.

## Measures

Proposed (nothing collects them yet):

- Days with at least one reading in the last 30 days.
- Readings per `metric_type` per month (needs a filter on `metric_type`, which the cell does not
  declare yet).
- 5xx rate and p95 latency on `/v1/health-metrics` (Sentry and uptime worker).

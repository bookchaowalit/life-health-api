# SPEC-001 — L2 baseline: locked dependencies, strict types, domain rules under test

Standard: ADR-0004 — TDD + SDD (architecture-docs, `docs/architecture/decisions/ADR-0004-tdd-sdd-standard.md`).
Big Loop Plan Wave 2 (solo-empire `repository-catalog/roadmaps/BIG-LOOP-PLAN-2026-10-21.md`).

## Document control

| Field | Value |
|---|---|
| Spec ID / version | SPEC-001 / 1.0 |
| Status | in review (implemented; owner approval pending) |
| Repository / path | bookchaowalit/life-health-api / `specs/001-l2-baseline/spec.md` |
| Owner (maker) | Claude Code (Wave 2 cells session) |
| Reviewer (checker) | Fresh Claude reviewer session (no maker context) |
| Approver | Owner (bookchaowalit): pending, see the Wave 2 report owner actions |
| Requirement links | Big Loop DoD L2: `PRODUCT.md`, ≥ 3 test files, Sentry, type check; L1 lockfile |
| Main-only | yes: committed straight to `main`, so the red run is local (ADR-0004 rule 2, v1.1) |
| Created / approved | 2026-10-22 / pending owner |

## 1. Problem and intent

- **Problem:** Dependencies were installed unpinned, there was no type check, the only tests were the generic contract suite, and a NaN or Infinity value is accepted and read back as null.
- **Outcome:** the image installs exactly `uv.lock` (`uv sync --frozen`), CI runs Ruff, mypy
  (strict on `src/`) and a coverage gate on shared CI v1.1.1, and the cell's own rules have
  tests of their own beyond the generic contract suite.
- **Why now:** Wave 2 of the Big Loop Plan; milestone M1 is 2026-11-15.

## 2. Scope

| In scope | Out of scope (non-goals) |
|---|---|
| `uv.lock`, Dockerfile, CI caller bump, Ruff/mypy config and fixes, domain tests, `PRODUCT.md` | New endpoints or fields; database migrations; a shared cellkit package (owner decision 2026-10-21: each service owns its code) |

## 3. Behaviour — scenarios

### AC-01 — A reading needs a source, type, value and time

- **Given** an owner with write permission
- **When** they create a reading without one of source, metric_type, value or recorded_at, or with an empty source or type
- **Then** the API answers 422 in every case
- **Test:** `tests/test_health_metric_validation.py::test_a_reading_needs_a_source_a_type_a_value_and_a_time` · level: integration (API + throwaway PostgreSQL)

### AC-02 — The value must be a number

- **Given** a reading body
- **When** `value` is text, null or a list, or is a decimal, zero or negative number
- **Then** text, null and list are refused with 422; the numbers are stored exactly
- **Test:** `tests/test_health_metric_validation.py::test_the_value_must_be_a_number` · level: integration (API + throwaway PostgreSQL)

### AC-03 — Required fields cannot be cleared on update

- **Given** a stored reading
- **When** a patch sets source, metric_type, value or recorded_at to null
- **Then** the API answers 422 `invalid_value` naming the field and the version stays 1; `unit` and `metadata` can be cleared
- **Test:** `tests/test_health_metric_validation.py::test_required_fields_cannot_be_cleared_on_update` · level: integration (API + throwaway PostgreSQL)

### AC-04 — Readings are not deduplicated

- **Given** an owner
- **When** they create two identical readings
- **Then** both are stored with different ids
- **Test:** `tests/test_health_metric_defaults.py::test_readings_are_not_deduplicated` · level: integration (API + throwaway PostgreSQL)

### AC-05 — The cell has no filters

- **Given** stored readings
- **When** the owner lists by `source` or `metric_type`, or asks for stats with any `group_by`
- **Then** the API answers 422 `unknown_filter` for the list and 422 for the stats; paging, `id`, `null` and `updated_since` still work
- **Test:** `tests/test_health_metric_queries.py::test_this_cell_has_no_field_filters` · level: integration (API + throwaway PostgreSQL)

### AC-06 — Another workspace cannot see a reading

- **Given** a reading written in one workspace
- **When** an owner of a different workspace reads, patches, lists or deletes it
- **Then** read, patch and delete answer 404 and the list is empty; the author still reads it unchanged
- **Test:** `tests/test_health_metric_queries.py::test_another_workspace_cannot_see_a_reading` · level: integration (API + throwaway PostgreSQL)

### AC-07 — A patch bumps the version only when something changed

- **Given** a reading at version 1
- **When** the owner corrects the value, then resends stored values
- **Then** the correction gives version 2, the unchanged patch keeps the version; a stale `expected_version` answers 409
- **Test:** `tests/test_health_metric_queries.py::test_a_patch_that_changes_nothing_keeps_the_version` · level: integration (API + throwaway PostgreSQL)

### AC-08 — A value that is not a finite number is refused

- **Given** a create request whose JSON value is NaN or Infinity
- **When** the owner posts it
- **Then** the API answers 422 instead of storing a reading that reads back as null
- **Test:** `tests/test_health_metric_defaults.py::test_a_value_that_is_not_a_finite_number_is_refused` · level: integration (API + throwaway PostgreSQL)

## 4. Interfaces and data

| Interface | Change | Contract |
|---|---|---|
| `/v1/*` (all resources) | unchanged | same routes and payloads; see README |

- **Data model / migration:** N/A — no schema change. Range rules are checked by the API on
  create and update; rows already stored are not rewritten.
- **Backward compatibility:** clients keep the same routes. A write that would store a range
  ending before it starts now gets `422 invalid_value` instead of `201/200`.

## 5. Non-functional requirements

| NFR | Target | How it is tested |
|---|---|---|
| Performance | N/A — no hot-path change beyond one comparison per declared range | — |
| Security / privacy | Same authorization, RLS and Sentry scrubbing as before | contract suite (`tests/test_contract.py`), `tests/test_sentry.py` |
| Reliability / observability | Reproducible image from `uv.lock`; failed inline publishes reach Sentry | image rehearsal before push; `test_inline_publish_failure_is_reported` |
| Accessibility / UX | N/A — API only | — |

## 6. Test plan (TDD)

- **Test levels:** integration tests against the FastAPI app with a throwaway local PostgreSQL
  (pgserver) and a fake platform; no hosted database or platform.
- **Test data:** generated in each test; no production data.
- **Coverage:** CI gate `coverage-threshold: "54"` (measured 56.40% on 2026-10-22, minus 2 points).
- **Not test-first (exceptions):** tests that pin behaviour the service already had
  (characterization tests, marked below) were written after the code by nature; tooling and
  config changes are covered by CI itself.

### Red / green log

| Scenario | Test | Red: commit / run + failure message | Green: commit / run | Refactor note |
|---|---|---|---|---|
| AC-01 | `tests/test_health_metric_validation.py::test_a_reading_needs_a_source_a_type_a_value_and_a_time` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-02 | `tests/test_health_metric_validation.py::test_the_value_must_be_a_number` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-03 | `tests/test_health_metric_validation.py::test_required_fields_cannot_be_cleared_on_update` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-04 | `tests/test_health_metric_defaults.py::test_readings_are_not_deduplicated` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-05 | `tests/test_health_metric_queries.py::test_this_cell_has_no_field_filters` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-06 | `tests/test_health_metric_queries.py::test_another_workspace_cannot_see_a_reading` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-07 | `tests/test_health_metric_queries.py::test_a_patch_that_changes_nothing_keeps_the_version` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-08 | `tests/test_health_metric_defaults.py::test_a_value_that_is_not_a_finite_number_is_refused` | 4010049 · kept as `xfail(strict=True)`: known cellkit bug (non-finite real accepted), fixed in the follow-up cellkit commit | CI run of the pushed tip | none |

## 7. Risks and open questions

| # | Risk or question | Impact | Owner | Resolution / date |
|---|---|---|---|---|
| 1 | Stored rows written before a range rule existed may already be inverted | a patch touching one of those dates is refused until both are fixed | owner | patches that do not touch the range still work |

## 8. Change log

| Version | Date | Change | Scenarios affected | Approved by |
|---|---|---|---|---|
| 1.0 | 2026-10-22 | Implemented with the Wave 2 baseline | all | pending owner |

## Approval

| Gate | Role | Name / date | Decision | Evidence |
|---|---|---|---|---|
| Implemented (DoD) | Reviewer (checker) | Fresh Claude reviewer / 2026-10-22 | see Wave 2 report | CI run of the pushed tip |
| Implemented (DoD) | Approver | Owner | pending | Wave 2 report |

"""What a stored health reading looks like and the rules that are NOT constraints."""

import pytest
from health_helpers import METRICS, create


def test_a_reading_keeps_exactly_what_was_sent(client, owner):
    response = create(
        client,
        owner,
        source="garmin",
        metric_type="resting_heart_rate",
        value=54,
        unit="bpm",
        metadata='{"device": "watch"}',
    )
    assert response.status_code == 201, response.text
    reading = client.get(f"{METRICS}/{response.json()['id']}", headers=owner).json()
    assert reading["source"] == "garmin"
    assert reading["metric_type"] == "resting_heart_rate"
    assert reading["value"] == 54
    assert reading["unit"] == "bpm"
    assert reading["metadata"] == '{"device": "watch"}'
    assert reading["recorded_at"].startswith("2026-10-10")
    assert reading["version"] == 1


def test_unit_and_metadata_are_empty_unless_given(client, owner):
    reading = create(client, owner).json()
    assert reading["unit"] is None
    assert reading["metadata"] is None


def test_metadata_is_free_text_not_json(client, owner):
    response = create(client, owner, metadata="felt tired after lunch")
    assert response.status_code == 201, response.text
    assert response.json()["metadata"] == "felt tired after lunch"


def test_source_and_metric_type_are_free_text(client, owner):
    response = create(
        client, owner, source="manual entry", metric_type="Blood Pressure (sys)"
    )
    assert response.status_code == 201, response.text


def test_readings_are_not_deduplicated(client, owner):
    first = create(client, owner)
    second = create(client, owner)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]


def test_a_reading_keeps_the_old_id_when_it_is_imported(client, owner):
    imported = create(client, owner, legacy_id=3141)
    assert imported.status_code == 201, imported.text
    assert imported.json()["id"] == 3141
    found = client.get(f"{METRICS}/legacy/3141", headers=owner)
    assert found.status_code == 200
    assert found.json()["value"] == 72.5
    assert create(client, owner, legacy_id=3141).status_code == 409


@pytest.mark.parametrize("not_a_number", ["NaN", "Infinity", "-Infinity"])
def test_a_value_that_is_not_a_finite_number_is_refused(client, owner, not_a_number):
    raw = (
        '{"source": "scale", "metric_type": "weight", "value": '
        + not_a_number
        + ', "recorded_at": "2026-10-10T06:30:00Z"}'
    )
    response = client.post(
        METRICS, headers={**owner, "content-type": "application/json"}, content=raw
    )
    assert response.status_code == 422

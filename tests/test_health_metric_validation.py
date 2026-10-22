"""What the health cell refuses: missing readings, non-numbers and bad timestamps."""

from health_helpers import METRICS, create


def test_a_reading_needs_a_source_a_type_a_value_and_a_time(client, owner):
    complete = {
        "source": "scale",
        "metric_type": "weight",
        "value": 72.5,
        "recorded_at": "2026-10-10T06:30:00+00:00",
    }
    for missing in complete:
        body = {k: v for k, v in complete.items() if k != missing}
        response = client.post(METRICS, headers=owner, json=body)
        assert response.status_code == 422, missing


def test_source_and_metric_type_cannot_be_empty(client, owner):
    assert create(client, owner, source="").status_code == 422
    assert create(client, owner, metric_type="").status_code == 422


def test_the_value_must_be_a_number(client, owner):
    assert create(client, owner, value="heavy").status_code == 422
    assert create(client, owner, value=None).status_code == 422
    assert create(client, owner, value=[72.5]).status_code == 422


def test_the_value_may_be_whole_decimal_zero_or_negative(client, owner):
    for value in (72, 72.25, 0, -3.5):
        response = create(client, owner, value=value)
        assert response.status_code == 201, value
        assert response.json()["value"] == value


def test_recorded_at_must_be_a_timestamp(client, owner):
    assert create(client, owner, recorded_at="this morning").status_code == 422
    assert create(client, owner, recorded_at="2026-10-10T06:30:00Z").status_code == 201


def test_a_reading_refuses_fields_it_does_not_have(client, owner):
    assert create(client, owner, mood="good").status_code == 422


def test_required_fields_cannot_be_cleared_on_update(client, owner):
    reading = create(client, owner).json()
    path = f"{METRICS}/{reading['id']}"
    for field in ("source", "metric_type", "value", "recorded_at"):
        cleared = client.patch(path, headers=owner, json={field: None})
        assert cleared.status_code == 422, field
        assert cleared.json()["detail"] == {"error": "invalid_value", "fields": [field]}
    assert client.get(path, headers=owner).json()["version"] == 1


def test_unit_and_metadata_may_be_left_out_or_cleared(client, owner):
    reading = create(client, owner, unit="kg", metadata="{}").json()
    path = f"{METRICS}/{reading['id']}"
    cleared = client.patch(path, headers=owner, json={"unit": None, "metadata": None})
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["unit"] is None
    assert cleared.json()["metadata"] is None

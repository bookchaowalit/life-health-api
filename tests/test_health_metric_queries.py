"""Listing, grouping, privacy and the lifecycle of a health reading."""

from health_helpers import METRICS, another_workspace, create


def ids(response):
    assert response.status_code == 200, response.text
    return [item["id"] for item in response.json()["items"]]


def test_readings_are_listed_oldest_first_and_newest_first_on_request(client, owner):
    first = create(client, owner, value=70).json()
    second = create(client, owner, value=71).json()
    assert ids(client.get(METRICS, headers=owner)) == [first["id"], second["id"]]
    newest = client.get(METRICS, headers=owner, params={"order": "desc"})
    assert ids(newest) == [second["id"], first["id"]]


def test_readings_can_be_paged(client, owner):
    made = [create(client, owner, value=v).json()["id"] for v in (1, 2, 3)]
    page = client.get(METRICS, headers=owner, params={"limit": 2})
    assert ids(page) == made[:2]
    rest = client.get(METRICS, headers=owner, params={"limit": 2, "offset": 2})
    assert ids(rest) == made[2:]
    after = client.get(METRICS, headers=owner, params={"after_id": made[0]})
    assert ids(after) == made[1:]


def test_this_cell_has_no_field_filters(client, owner):
    create(client, owner)
    for field in ("source", "metric_type", "recorded_at", "value"):
        refused = client.get(METRICS, headers=owner, params={field: "scale"})
        assert refused.status_code == 422, field
        assert refused.json()["detail"] == {
            "error": "unknown_filter",
            "fields": [field],
        }


def test_readings_can_be_found_by_id_and_by_missing_unit(client, owner):
    with_unit = create(client, owner, unit="kg").json()
    without_unit = create(client, owner).json()
    by_id = client.get(METRICS, headers=owner, params={"id": with_unit["id"]})
    assert ids(by_id) == [with_unit["id"]]
    no_unit = client.get(METRICS, headers=owner, params={"null": "unit"})
    assert ids(no_unit) == [without_unit["id"]]


def test_readings_can_be_listed_since_a_time(client, owner):
    create(client, owner)
    future = client.get(
        METRICS, headers=owner, params={"updated_since": "2999-01-01T00:00:00Z"}
    )
    assert ids(future) == []
    past = client.get(
        METRICS, headers=owner, params={"updated_since": "2000-01-01T00:00:00Z"}
    )
    assert len(ids(past)) == 1


def test_stats_cannot_group_readings_because_there_are_no_filters(client, owner):
    create(client, owner)
    for field in ("source", "metric_type", "unit", "recorded_at", "value", ""):
        stats = client.get(
            f"{METRICS}/stats", headers=owner, params={"group_by": field}
        )
        assert stats.status_code == 422, field
        assert stats.json()["detail"] == {
            "error": "invalid_value",
            "fields": ["group_by"],
        }


def test_another_workspace_cannot_see_a_reading(client, owner, harness, platform):
    stranger = another_workspace(harness, platform)
    reading = create(client, owner).json()
    assert client.get(f"{METRICS}/{reading['id']}", headers=stranger).status_code == 404
    assert ids(client.get(METRICS, headers=stranger)) == []
    assert (
        client.patch(
            f"{METRICS}/{reading['id']}", headers=stranger, json={"value": 1}
        ).status_code
        == 404
    )
    assert (
        client.delete(f"{METRICS}/{reading['id']}", headers=stranger).status_code == 404
    )
    assert (
        client.get(f"{METRICS}/{reading['id']}", headers=owner).json()["value"] == 72.5
    )


def test_correcting_a_reading_bumps_the_version(client, owner):
    reading = create(client, owner, value=72.5).json()
    path = f"{METRICS}/{reading['id']}"
    corrected = client.patch(path, headers=owner, json={"value": 72.1, "unit": "kg"})
    assert corrected.status_code == 200, corrected.text
    assert corrected.json()["version"] == 2
    assert corrected.json()["value"] == 72.1
    assert corrected.json()["source"] == "scale"


def test_a_patch_that_changes_nothing_keeps_the_version(client, owner):
    reading = create(client, owner, unit="kg").json()
    path = f"{METRICS}/{reading['id']}"
    same = client.patch(path, headers=owner, json={"value": 72.5, "unit": "kg"})
    assert same.status_code == 200, same.text
    assert same.json()["version"] == 1
    assert same.json()["updated_at"] == reading["updated_at"]


def test_a_stale_expected_version_is_refused(client, owner):
    reading = create(client, owner).json()
    path = f"{METRICS}/{reading['id']}"
    assert client.patch(path, headers=owner, json={"value": 73}).status_code == 200
    stale = client.patch(path, headers=owner, json={"value": 74, "expected_version": 1})
    assert stale.status_code == 409
    assert stale.json()["detail"] == {"error": "version_conflict", "version": 2}


def test_a_deleted_reading_is_gone(client, owner):
    reading = create(client, owner).json()
    path = f"{METRICS}/{reading['id']}"
    assert client.delete(path, headers=owner).status_code == 204
    assert client.get(path, headers=owner).status_code == 404
    assert client.delete(path, headers=owner).status_code == 404

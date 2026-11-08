from datetime import datetime
import sqlite3
from uuid import uuid4

import pytest

from backend.main import create_app


@pytest.fixture
def app(tmp_path):
    return create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / "devices.sqlite3"),
            "API_TOKEN": "test-token",
        }
    )


@pytest.fixture
def client(app):
    return app.test_client()


def auth_headers():
    return {"Authorization": "Bearer test-token"}


def register(client, device_id=None, **extra):
    return client.post(
        "/api/v1/devices/register",
        headers=auth_headers(),
        json={
            "device_id": device_id or str(uuid4()),
            "hostname": "lab-pc-01",
            "platform": "Windows 11",
            **extra,
        },
    )


def event_payload(device_id, **extra):
    return {
        "event_id": str(uuid4()),
        "device_id": device_id,
        "event_type": "demo",
        "severity": "info",
        "occurred_at": "2026-01-02T03:04:05.123Z",
        "metadata": {"source": "test", "purpose": "synthetic event"},
        **extra,
    }


def ingest(client, events, **kwargs):
    return client.post(
        "/api/v1/events/batch",
        headers=kwargs.pop("headers", auth_headers()),
        json={"events": events},
        **kwargs,
    )


def test_registration_and_listing(client):
    device_id = str(uuid4())
    response = register(client, device_id)

    assert response.status_code == 201
    device = response.json["device"]
    assert device["device_id"] == device_id
    assert device["hostname"] == "lab-pc-01"
    assert device["platform"] == "Windows 11"
    assert device["registered_at"].endswith("Z")
    registered_at = datetime.fromisoformat(device["registered_at"].replace("Z", "+00:00"))
    assert registered_at.utcoffset().total_seconds() == 0

    listing = client.get("/api/v1/devices", headers=auth_headers())
    assert listing.status_code == 200
    assert listing.json["devices"] == [device]


def test_duplicate_registration_returns_conflict(client):
    device_id = str(uuid4())
    assert register(client, device_id).status_code == 201

    response = register(client, device_id)

    assert response.status_code == 409
    assert response.json == {"error": "device_already_registered"}


def test_registration_persists_across_app_instances(tmp_path):
    database = str(tmp_path / "persistent.sqlite3")
    first_client = create_app({"TESTING": True, "DATABASE": database, "API_TOKEN": "test-token"}).test_client()
    device_id = str(uuid4())
    assert register(first_client, device_id).status_code == 201

    second_client = create_app({"TESTING": True, "DATABASE": database, "API_TOKEN": "test-token"}).test_client()
    response = second_client.get("/api/v1/devices", headers=auth_headers())

    assert response.status_code == 200
    assert response.json["devices"][0]["device_id"] == device_id


def test_heartbeat_updates_last_seen(client):
    device_id = str(uuid4())
    registered = register(client, device_id).json["device"]

    response = client.post(
        f"/api/v1/devices/{device_id}/heartbeat",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    assert response.json["device_id"] == device_id
    assert response.json["last_seen_at"].endswith("Z")
    assert response.json["last_seen_at"] >= registered["last_seen_at"]


@pytest.mark.parametrize(
    "payload",
    [
        {"device_id": "not-a-uuid", "hostname": "pc", "platform": "Windows"},
        {"device_id": str(uuid4()), "hostname": " ", "platform": "Windows"},
        {"device_id": str(uuid4()), "hostname": "pc", "platform": "Windows", "unexpected": True},
    ],
)
def test_invalid_registration_input_returns_bad_request(client, payload):
    response = client.post(
        "/api/v1/devices/register",
        headers=auth_headers(),
        json=payload,
    )

    assert response.status_code == 400


def test_unauthorized_device_requests_are_rejected(client):
    response = client.get("/api/v1/devices")

    assert response.status_code == 401
    assert response.json == {"error": "unauthorized"}


def test_event_batch_ingestion_acknowledges_and_persists(client, app):
    device_id = str(uuid4())
    assert register(client, device_id).status_code == 201
    event = event_payload(device_id)

    response = ingest(client, [event])

    assert response.status_code == 200
    assert response.json == {
        "acknowledged_event_ids": [event["event_id"]],
        "rejected_events": [],
    }
    with sqlite3.connect(app.config["DATABASE"]) as connection:
        stored = connection.execute(
            "SELECT device_id, event_type, severity, occurred_at, metadata_json "
            "FROM events WHERE event_id = ?",
            (event["event_id"],),
        ).fetchone()
    assert stored == (
        device_id,
        "demo",
        "info",
        "2026-01-02T03:04:05.123000Z",
        '{"purpose":"synthetic event","source":"test"}',
    )


def test_duplicate_event_is_acknowledged_without_creating_another_row(client, app):
    device_id = str(uuid4())
    assert register(client, device_id).status_code == 201
    event = event_payload(device_id)

    assert ingest(client, [event]).status_code == 200
    duplicate = ingest(client, [event])

    assert duplicate.status_code == 200
    assert duplicate.json["acknowledged_event_ids"] == [event["event_id"]]
    with sqlite3.connect(app.config["DATABASE"]) as connection:
        assert connection.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1


def test_event_id_owned_by_another_device_is_not_acknowledged(client, app):
    original_device = str(uuid4())
    other_device = str(uuid4())
    assert register(client, original_device).status_code == 201
    assert register(client, other_device).status_code == 201
    original_event = event_payload(original_device)
    assert ingest(client, [original_event]).status_code == 200
    conflicting_event = {**original_event, "device_id": other_device}

    response = ingest(client, [conflicting_event])

    assert response.status_code == 200
    assert response.json == {
        "acknowledged_event_ids": [],
        "rejected_events": [
            {
                "event_id": original_event["event_id"],
                "error": "event_id_owned_by_another_device",
            }
        ],
    }
    with sqlite3.connect(app.config["DATABASE"]) as connection:
        owner = connection.execute(
            "SELECT device_id FROM events WHERE event_id = ?",
            (original_event["event_id"],),
        ).fetchone()[0]
    assert owner == original_device


def test_event_batch_requires_authentication(client):
    response = client.post(
        "/api/v1/events/batch",
        json={"events": [event_payload(str(uuid4()))]},
    )

    assert response.status_code == 401
    assert response.json == {"error": "unauthorized"}


@pytest.mark.parametrize(
    "event_changes",
    [
        {"event_id": "not-a-uuid"},
        {"device_id": "not-a-uuid"},
        {"event_type": ""},
        {"severity": "urgent"},
        {"occurred_at": "not-a-timestamp"},
        {"occurred_at": "2026-01-02T03:04:05"},
        {"metadata": ["not", "an", "object"]},
        {"file_content": "raw sensitive content"},
    ],
)
def test_malformed_events_are_rejected(client, event_changes):
    device_id = str(uuid4())
    event = {**event_payload(device_id), **event_changes}

    response = ingest(client, [event])

    assert response.status_code == 400
    assert response.json == {"error": "invalid_event"}


def test_unknown_event_device_is_rejected_without_persisting(client, app):
    registered_device = str(uuid4())
    assert register(client, registered_device).status_code == 201
    events = [
        event_payload(registered_device),
        event_payload(str(uuid4())),
    ]

    response = ingest(client, events)

    assert response.status_code == 404
    assert response.json == {"error": "device_not_found"}
    with sqlite3.connect(app.config["DATABASE"]) as connection:
        assert connection.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0


def test_event_persists_across_app_instances(tmp_path):
    database = str(tmp_path / "persistent.sqlite3")
    first_client = create_app(
        {"TESTING": True, "DATABASE": database, "API_TOKEN": "test-token"}
    ).test_client()
    device_id = str(uuid4())
    assert register(first_client, device_id).status_code == 201
    event = event_payload(device_id)
    assert ingest(first_client, [event]).status_code == 200

    second_client = create_app(
        {"TESTING": True, "DATABASE": database, "API_TOKEN": "test-token"}
    ).test_client()
    response = ingest(second_client, [event])

    assert response.status_code == 200
    assert response.json["acknowledged_event_ids"] == [event["event_id"]]


def test_event_batch_is_bounded(client):
    response = ingest(client, [event_payload(str(uuid4())) for _ in range(101)])

    assert response.status_code == 400
    assert response.json == {"error": "invalid_event_batch_size"}


def test_event_request_size_is_limited(client):
    oversized_body = b'{"events": []}' + b" " * (64 * 1024)
    response = client.post(
        "/api/v1/events/batch",
        headers={**auth_headers(), "Content-Type": "application/json"},
        data=oversized_body,
    )

    assert response.status_code == 413
    assert response.json == {"error": "request_too_large"}


def test_health_response_is_unchanged(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json == {"status": "ok", "message": "DLP Backend is running"}

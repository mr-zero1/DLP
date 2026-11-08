import hmac
import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from flask import Flask, jsonify, request
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge


DEFAULT_HOST = "192.168.122.1"
DEFAULT_PORT = 5000
DEFAULT_DATABASE = Path.home() / ".local" / "share" / "neon-sentinel" / "devices.sqlite3"
MAX_REQUEST_BYTES = 64 * 1024
MAX_DEVICE_REQUEST_BYTES = 16 * 1024
MAX_EVENT_BATCH_SIZE = 100
MAX_EVENT_METADATA_BYTES = 8 * 1024
VALID_EVENT_SEVERITIES = {"info", "low", "medium", "high", "critical"}


def _utc_timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _connect(database):
    connection = sqlite3.connect(database, timeout=5)
    connection.row_factory = sqlite3.Row
    return connection


def _initialize_database(database):
    Path(database).parent.mkdir(parents=True, exist_ok=True)
    with closing(_connect(database)) as connection:
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS devices (
                    device_id TEXT PRIMARY KEY,
                    hostname TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    registered_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    device_id TEXT NOT NULL REFERENCES devices(device_id),
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    received_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS events_device_occurred "
                "ON events(device_id, occurred_at)"
            )


def _device_from_row(row):
    return {
        "device_id": row["device_id"],
        "hostname": row["hostname"],
        "platform": row["platform"],
        "registered_at": row["registered_at"],
        "last_seen_at": row["last_seen_at"],
    }


def _read_json_object():
    if not request.is_json:
        return None, (jsonify(error="content_type_must_be_application_json"), 400)
    try:
        payload = request.get_json()
    except BadRequest:
        return None, (jsonify(error="invalid_json"), 400)
    if not isinstance(payload, dict):
        return None, (jsonify(error="json_object_required"), 400)
    return payload, None


def _valid_device_id(value):
    if not isinstance(value, str):
        return False
    try:
        return str(UUID(value)) == value.lower()
    except ValueError:
        return False


def _valid_text(value, maximum):
    return (
        isinstance(value, str)
        and 0 < len(value.strip()) <= maximum
        and not any(ord(character) < 32 or ord(character) == 127 for character in value)
    )


def _parse_event(value):
    required_fields = {
        "event_id",
        "device_id",
        "event_type",
        "severity",
        "occurred_at",
        "metadata",
    }
    if not isinstance(value, dict) or set(value) != required_fields:
        return None

    event_id = value["event_id"]
    device_id = value["device_id"]
    event_type = value["event_type"]
    severity = value["severity"]
    occurred_at = value["occurred_at"]
    metadata = value["metadata"]
    if (
        not _valid_device_id(event_id)
        or not _valid_device_id(device_id)
        or not _valid_text(event_type, 100)
        or not isinstance(severity, str)
        or severity.lower() not in VALID_EVENT_SEVERITIES
        or not isinstance(metadata, dict)
    ):
        return None

    try:
        parsed_time = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
        if parsed_time.tzinfo is None or parsed_time.utcoffset() is None:
            return None
        metadata_json = json.dumps(
            metadata,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (AttributeError, TypeError, ValueError):
        return None

    if len(metadata_json.encode("utf-8")) > MAX_EVENT_METADATA_BYTES:
        return None

    return {
        "event_id": event_id.lower(),
        "device_id": device_id.lower(),
        "event_type": event_type.strip(),
        "severity": severity.lower(),
        "occurred_at": parsed_time.astimezone(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z"),
        "metadata_json": metadata_json,
    }


def create_app(config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE=os.environ.get("NEON_SENTINEL_DB_PATH", str(DEFAULT_DATABASE)),
        API_TOKEN=os.environ.get("NEON_SENTINEL_API_TOKEN"),
        HOST=os.environ.get("NEON_SENTINEL_HOST", DEFAULT_HOST),
        PORT=int(os.environ.get("NEON_SENTINEL_PORT", str(DEFAULT_PORT))),
        MAX_CONTENT_LENGTH=MAX_REQUEST_BYTES,
    )
    if config:
        app.config.update(config)
    if not isinstance(app.config["PORT"], int) or not 1 <= app.config["PORT"] <= 65535:
        raise ValueError("PORT must be an integer between 1 and 65535")

    _initialize_database(app.config["DATABASE"])

    @app.errorhandler(RequestEntityTooLarge)
    def request_too_large(_error):
        return jsonify(error="request_too_large"), 413

    @app.before_request
    def authenticate_device_api():
        if not request.path.startswith(("/api/v1/devices", "/api/v1/events")):
            return None

        configured_token = app.config["API_TOKEN"]
        if not isinstance(configured_token, str) or not configured_token:
            return jsonify(error="server_authentication_not_configured"), 503

        scheme, separator, supplied_token = request.headers.get("Authorization", "").partition(" ")
        valid = (
            separator == " "
            and scheme.lower() == "bearer"
            and hmac.compare_digest(supplied_token.encode("utf-8"), configured_token.encode("utf-8"))
        )
        if not valid:
            return jsonify(error="unauthorized"), 401
        if request.path.startswith("/api/v1/devices") and (
            request.content_length is not None
            and request.content_length > MAX_DEVICE_REQUEST_BYTES
        ):
            return jsonify(error="request_too_large"), 413
        return None

    @app.get("/api/v1/health")
    def health():
        return jsonify(
            {
                "status": "ok",
                "message": "DLP Backend is running",
            }
        )

    @app.post("/api/v1/devices/register")
    def register_device():
        payload, error = _read_json_object()
        if error:
            return error

        required_fields = {"device_id", "hostname", "platform"}
        if set(payload) != required_fields:
            return jsonify(error="device_id_hostname_and_platform_required"), 400
        device_id = payload["device_id"]
        hostname = payload["hostname"]
        platform = payload["platform"]
        if (
            not _valid_device_id(device_id)
            or not _valid_text(hostname, 255)
            or not _valid_text(platform, 100)
        ):
            return jsonify(error="invalid_device_fields"), 400

        timestamp = _utc_timestamp()
        try:
            with closing(_connect(app.config["DATABASE"])) as connection:
                with connection:
                    connection.execute(
                        """
                        INSERT INTO devices (device_id, hostname, platform, registered_at, last_seen_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (device_id.lower(), hostname.strip(), platform.strip(), timestamp, timestamp),
                    )
        except sqlite3.IntegrityError:
            return jsonify(error="device_already_registered"), 409

        return jsonify(
            device={
                "device_id": device_id.lower(),
                "hostname": hostname.strip(),
                "platform": platform.strip(),
                "registered_at": timestamp,
                "last_seen_at": timestamp,
            }
        ), 201

    @app.post("/api/v1/devices/<device_id>/heartbeat")
    def heartbeat(device_id):
        if not _valid_device_id(device_id):
            return jsonify(error="invalid_device_id"), 400

        timestamp = _utc_timestamp()
        with closing(_connect(app.config["DATABASE"])) as connection:
            with connection:
                cursor = connection.execute(
                    "UPDATE devices SET last_seen_at = ? WHERE device_id = ?",
                    (timestamp, device_id.lower()),
                )
        if cursor.rowcount == 0:
            return jsonify(error="device_not_found"), 404
        return jsonify(device_id=device_id.lower(), last_seen_at=timestamp)

    @app.get("/api/v1/devices")
    def list_devices():
        with closing(_connect(app.config["DATABASE"])) as connection:
            rows = connection.execute(
                "SELECT device_id, hostname, platform, registered_at, last_seen_at "
                "FROM devices ORDER BY registered_at, device_id"
            ).fetchall()
        return jsonify(devices=[_device_from_row(row) for row in rows])

    @app.post("/api/v1/events/batch")
    def ingest_event_batch():
        payload, error = _read_json_object()
        if error:
            return error
        if set(payload) != {"events"} or not isinstance(payload["events"], list):
            return jsonify(error="events_array_required"), 400
        if not payload["events"] or len(payload["events"]) > MAX_EVENT_BATCH_SIZE:
            return jsonify(error="invalid_event_batch_size"), 400

        events = []
        seen_event_ids = set()
        for item in payload["events"]:
            event = _parse_event(item)
            if event is None:
                return jsonify(error="invalid_event"), 400
            if event["event_id"] in seen_event_ids:
                return jsonify(error="duplicate_event_id_in_batch"), 400
            seen_event_ids.add(event["event_id"])
            events.append(event)

        device_ids = {event["device_id"] for event in events}
        acknowledged_event_ids = []
        rejected_events = []
        with closing(_connect(app.config["DATABASE"])) as connection:
            with connection:
                registered_ids = {
                    row["device_id"]
                    for row in connection.execute(
                        "SELECT device_id FROM devices WHERE device_id IN "
                        f"({','.join('?' for _ in device_ids)})",
                        tuple(device_ids),
                    ).fetchall()
                }
                if registered_ids != device_ids:
                    return jsonify(error="device_not_found"), 404

                received_at = _utc_timestamp()
                for event in events:
                    connection.execute(
                        """
                        INSERT INTO events (
                            event_id, device_id, event_type, severity,
                            occurred_at, metadata_json, received_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(event_id) DO NOTHING
                        """,
                        (
                            event["event_id"],
                            event["device_id"],
                            event["event_type"],
                            event["severity"],
                            event["occurred_at"],
                            event["metadata_json"],
                            received_at,
                        ),
                    )
                    existing = connection.execute(
                        "SELECT device_id FROM events WHERE event_id = ?",
                        (event["event_id"],),
                    ).fetchone()
                    if existing["device_id"] == event["device_id"]:
                        acknowledged_event_ids.append(event["event_id"])
                    else:
                        rejected_events.append(
                            {
                                "event_id": event["event_id"],
                                "error": "event_id_owned_by_another_device",
                            }
                        )

        return jsonify(
            acknowledged_event_ids=acknowledged_event_ids,
            rejected_events=rejected_events,
        )

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host=app.config["HOST"], port=app.config["PORT"], debug=False)

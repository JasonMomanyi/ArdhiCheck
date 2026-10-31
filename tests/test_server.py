"""In-process tests for app.server HTTP handler (no external sockets needed)."""

import io
import json
import os
from pathlib import Path
from unittest.mock import MagicMock

from app.server import ArdhiCheckHandler


class MockServerRequest(ArdhiCheckHandler):
    """Subclass of ArdhiCheckHandler that captures output in memory."""

    def __init__(self, method: str, path: str, body: bytes = b""):
        self.rfile = io.BytesIO(body)
        self.wfile = io.BytesIO()
        self.command = method
        self.path = path
        self.requestline = f"{method} {path} HTTP/1.1"
        self.request_version = "HTTP/1.1"
        self.headers = {
            "Content-Length": str(len(body)),
            "Content-Type": "application/json",
        }
        self.server = MagicMock()
        self.client_address = ("127.0.0.1", 12345)
        self.close_connection = True

        if method == "GET":
            self.do_GET()
        elif method == "POST":
            self.do_POST()

    def log_message(self, format: str, *args: object) -> None:
        """Suppress stdout log messages during unit tests."""
        pass

    def get_response(self) -> tuple[int, dict, bytes]:
        """Extract HTTP status, headers, and body from wfile."""
        output = self.wfile.getvalue()
        parts = output.split(b"\r\n\r\n", 1)
        headers_raw = parts[0].decode("utf-8", errors="ignore")
        body = parts[1] if len(parts) > 1 else b""

        status_line = headers_raw.splitlines()[0] if headers_raw else ""
        status_code = int(status_line.split(" ")[1]) if " " in status_line else 200

        return status_code, {}, body


def test_server_health_handler():
    handler = MockServerRequest("GET", "/api/health")
    status, _, body = handler.get_response()
    assert status == 200
    data = json.loads(body.decode("utf-8"))
    assert data["status"] == "healthy"
    assert "muse-spark" in data["model"]
    assert "disclaimer" in data
    assert "Not legal advice" in data["disclaimer"]


def test_server_layers_handler():
    handler = MockServerRequest("GET", "/api/layers")
    status, _, body = handler.get_response()
    assert status == 200
    data = json.loads(body.decode("utf-8"))
    assert len(data) >= 4
    for lyr in data:
        assert "licence" in lyr
        assert "source" in lyr


def test_server_examples_handler():
    handler = MockServerRequest("GET", "/api/examples")
    status, _, body = handler.get_response()
    assert status == 200
    data = json.loads(body.decode("utf-8"))
    assert len(data) >= 4
    scenario_ids = [d["id"] for d in data]
    assert "scenario_1_clean" in scenario_ids


def test_server_check_post_handler():
    payload = json.dumps({"preset_hint": "scenario_1"}).encode("utf-8")
    handler = MockServerRequest("POST", "/api/check", body=payload)
    status, _, body = handler.get_response()
    assert status == 200
    data = json.loads(body.decode("utf-8"))
    assert data["verdict"] == "GREEN"
    assert "209" in data["lr_number"]
    assert "provenance" in data
    assert "disclaimer" in data


def test_server_static_index_handler():
    handler = MockServerRequest("GET", "/")
    status, _, body = handler.get_response()
    assert status == 200
    assert b"ArdhiCheck" in body


def test_server_screen_reserves_handler():
    coords = [[36.830, -1.240], [36.835, -1.240], [36.835, -1.245], [36.830, -1.245]]
    payload = json.dumps({"coords": coords, "riparian_buffer_m": 25.0}).encode("utf-8")
    handler = MockServerRequest("POST", "/api/screen-reserves", body=payload)
    status, _, body = handler.get_response()
    assert status == 200
    data = json.loads(body.decode("utf-8"))
    assert data["riparian_buffer_m"] == 25.0
    assert len(data["conflicts"]) >= 1
    assert "Karura Forest" in data["conflicts"][0]["name"]
    assert "disclaimer" in data


def test_server_test_meta_demo_handler():
    old_key = os.environ.pop("MODEL_API_KEY", None)
    try:
        handler = MockServerRequest("POST", "/api/test-meta", body=b"{}")
        status, _, body = handler.get_response()
        assert status == 200
        data = json.loads(body.decode("utf-8"))
        assert data["connected"] is False
        assert data["status"] == "Offline replay (pre-recorded)"
        assert "muse-spark" in data["model"]
    finally:
        if old_key is not None:
            os.environ["MODEL_API_KEY"] = old_key


def test_server_set_key_handler():
    dotenv_path = Path(".env")
    old_dotenv_text = dotenv_path.read_text(encoding="utf-8") if dotenv_path.is_file() else None
    old_key = os.environ.get("MODEL_API_KEY")
    try:
        payload = json.dumps({"api_key": "test_key_update"}).encode("utf-8")
        handler = MockServerRequest("POST", "/api/set-key", body=payload)
        status, _, body = handler.get_response()
        assert status == 200
        data = json.loads(body.decode("utf-8"))
        assert data["status"] == "ok"
        assert os.environ.get("MODEL_API_KEY") == "test_key_update"
    finally:
        if old_key is not None:
            os.environ["MODEL_API_KEY"] = old_key
        else:
            os.environ.pop("MODEL_API_KEY", None)
        if old_dotenv_text is not None:
            dotenv_path.write_text(old_dotenv_text, encoding="utf-8")

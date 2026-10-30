"""In-process tests for app.server HTTP handler (no external sockets needed)."""

import io
import json
import os
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
    assert "muse-spark-1.3" in data["model"]


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
    assert data["lr_number"] == "L.R. 209/14582"


def test_server_static_index_handler():
    handler = MockServerRequest("GET", "/")
    status, _, body = handler.get_response()
    assert status == 200
    assert b"ArdhiCheck" in body


def test_server_advisor_handler():
    coords = [[36.960, -1.145], [36.962, -1.145], [36.962, -1.147], [36.960, -1.147]]
    # 12-acre plot in Ruiru: fair market value is ~KES 350M
    payload = json.dumps({"coords": coords, "asking_price_kes": 350_000_000}).encode("utf-8")
    handler = MockServerRequest("POST", "/api/advisor", body=payload)
    status, _, body = handler.get_response()
    assert status == 200
    data = json.loads(body.decode("utf-8"))
    assert data["county"] == "Kiambu"
    assert data["decision_verdict"] == "CLEAR_BUY"
    assert data["valuation_kes_mid"] > 0
    assert data["is_safe_residential"] is True


def test_server_test_meta_demo_handler():
    # Ensure no API key set
    old_key = os.environ.pop("MODEL_API_KEY", None)
    try:
        handler = MockServerRequest("POST", "/api/test-meta", body=b"{}")
        status, _, body = handler.get_response()
        assert status == 200
        data = json.loads(body.decode("utf-8"))
        assert data["status"] == "demo_mode"
        assert data["model"] == "muse-spark-1.3"
    finally:
        if old_key is not None:
            os.environ["MODEL_API_KEY"] = old_key


def test_server_set_key_handler():
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

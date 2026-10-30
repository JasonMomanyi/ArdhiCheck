"""HTTP server for ArdhiCheck Web & Multiplatform Application.

Provides REST API endpoints and serves the modern frontend application.
Uses Python standard library http.server for zero external runtime web dependencies.
Strictly adheres to Meta Hackathon rules:
- Meta Muse models (muse-spark-1.3, optional muse-spark-open) and SAM 3.1.
- Honest offline replay reporting when live key is not configured.
- No valuation or buyer advice.
- Prominent disclaimers and data layer attributions.
"""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from app.geo.reserves import get_layer_metadata, screen_reserves_pure
from app.meta.client import MetaModelClient, load_env_file
from app.pipeline import LEGAL_DISCLAIMER, run_survey_audit

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "app" / "static"
EXAMPLES_DIR = BASE_DIR / "data" / "examples"

load_env_file()


class ArdhiCheckHandler(BaseHTTPRequestHandler):
    """HTTP request handler for ArdhiCheck."""

    def _send_json(self, data: dict | list, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, file_path: Path) -> None:
        if not file_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return

        mime_type, _ = mimetypes.guess_type(str(file_path))
        mime_type = mime_type or "application/octet-stream"
        data = file_path.read_bytes()

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        # Root and static files
        if path in ("/", "/index.html"):
            self._send_file(STATIC_DIR / "index.html")
            return

        if path.startswith("/static/"):
            rel_path = path.replace("/static/", "")
            self._send_file(STATIC_DIR / rel_path)
            return

        if path.startswith("/data/examples/"):
            rel_path = path.replace("/data/examples/", "")
            self._send_file(EXAMPLES_DIR / rel_path)
            return

        # API Endpoints
        if path == "/api/health":
            meta_client = MetaModelClient()
            mode_name = (
                "live"
                if meta_client.is_live
                else "Offline replay (pre-recorded)"
            )
            self._send_json(
                {
                    "status": "healthy",
                    "mode": mode_name,
                    "live_meta_api": meta_client.is_live,
                    "model": meta_client.model,
                    "base_url": meta_client.base_url,
                    "satellite_model": "sam-3.1",
                    "event": "Meta Global AI Developer Hackathon (Oct 26 - Nov 4, 2026)",
                    "disclaimer": LEGAL_DISCLAIMER,
                }
            )
            return

        if path == "/api/layers":
            self._send_json(get_layer_metadata())
            return

        if path == "/api/examples":
            examples = []
            if EXAMPLES_DIR.exists():
                for meta_file in sorted(EXAMPLES_DIR.glob("scenario_*.json")):
                    try:
                        info = json.loads(meta_file.read_text(encoding="utf-8"))
                        scenario_id = info.get("id")
                        plan_img = f"/data/examples/{meta_file.stem}_plan.png"
                        sat_img = f"/data/examples/{meta_file.stem}_satellite.png"
                        examples.append(
                            {
                                "id": scenario_id,
                                "title": info.get("title"),
                                "lr_number": info.get("lr_number"),
                                "locality": info.get("locality"),
                                "stated_area": (
                                    f"{info.get('stated_area')} {info.get('stated_unit', 'ha')}"
                                ),
                                "expected_verdict": info.get("expected_verdict"),
                                "plan_image_url": plan_img,
                                "satellite_image_url": sat_img,
                                "notes": info.get("notes", []),
                            }
                        )
                    except Exception:
                        continue
            self._send_json(examples)
            return

        if path.startswith("/api/examples/"):
            scenario_id = path.replace("/api/examples/", "")
            target_json = EXAMPLES_DIR / f"{scenario_id}.json"
            if not target_json.exists():
                matches = list(EXAMPLES_DIR.glob(f"*{scenario_id}*.json"))
                if matches:
                    target_json = matches[0]

            if target_json.exists():
                data = json.loads(target_json.read_text(encoding="utf-8"))
                self._send_json(data)
                return

            self.send_error(HTTPStatus.NOT_FOUND, f"Example {scenario_id} not found")
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Path not found")

    def do_POST(self) -> None:
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        if path == "/api/check":
            content_length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_length)

            try:
                payload = json.loads(body_bytes.decode("utf-8"))
            except Exception as e:
                self._send_json(
                    {"error": f"Invalid JSON payload: {e}"}, status=HTTPStatus.BAD_REQUEST
                )
                return

            preset_hint = payload.get("preset_hint")
            plan_b64 = payload.get("plan_image_b64")
            sat_b64 = payload.get("satellite_image_b64")
            document_text = payload.get("document_text")
            filename = payload.get("filename", "")
            manual_legs = payload.get("manual_legs")
            manual_lr = payload.get("manual_lr_number")
            manual_area = payload.get("manual_stated_area")
            manual_unit = payload.get("manual_stated_unit", "ha")
            crs_name = payload.get("crs_name", "arc1960_utm37s")
            tolerance_misclosure = float(payload.get("tolerance_misclosure_m", 0.30))
            tolerance_area = float(payload.get("tolerance_area_pct", 3.0))

            plan_bytes = None
            if plan_b64:
                try:
                    if "," in plan_b64:
                        plan_b64 = plan_b64.split(",", 1)[1]
                    plan_bytes = base64.b64decode(plan_b64)
                except Exception:
                    pass

            sat_bytes = None
            if sat_b64:
                try:
                    if "," in sat_b64:
                        sat_b64 = sat_b64.split(",", 1)[1]
                    sat_bytes = base64.b64decode(sat_b64)
                except Exception:
                    pass

            try:
                result = run_survey_audit(
                    plan_image_bytes=plan_bytes,
                    satellite_image_bytes=sat_bytes,
                    document_text=document_text,
                    filename=filename,
                    preset_hint=preset_hint,
                    manual_legs=manual_legs,
                    manual_lr_number=manual_lr,
                    manual_stated_area=float(manual_area) if manual_area is not None else None,
                    manual_stated_unit=manual_unit,
                    crs_name=crs_name,
                    tolerance_misclosure_m=tolerance_misclosure,
                    tolerance_area_pct=tolerance_area,
                )
                self._send_json(result)
            except Exception as exc:
                self._send_json(
                    {"error": f"Audit execution failed: {exc}"},
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                )
            return

        if path == "/api/screen-reserves":
            content_length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_length)
            try:
                payload = json.loads(body_bytes.decode("utf-8"))
            except Exception as e:
                self._send_json(
                    {"error": f"Invalid JSON payload: {e}"}, status=HTTPStatus.BAD_REQUEST
                )
                return

            raw_coords = payload.get("coords", [])
            riparian_buffer_m = float(payload.get("riparian_buffer_m", 30.0))
            coords: list[tuple[float, float]] = []
            for pt in raw_coords:
                if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                    coords.append((float(pt[0]), float(pt[1])))

            conflicts = screen_reserves_pure(coords, riparian_buffer_m=riparian_buffer_m)
            self._send_json(
                {
                    "conflicts": conflicts,
                    "count": len(conflicts),
                    "riparian_buffer_m": riparian_buffer_m,
                    "disclaimer": LEGAL_DISCLAIMER,
                }
            )
            return

        if path == "/api/test-meta":
            content_length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_length) if content_length > 0 else b"{}"
            try:
                payload = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
            except Exception:
                payload = {}

            api_key = payload.get("api_key") or os.environ.get("MODEL_API_KEY", "").strip()
            base_url = payload.get("base_url") or os.environ.get("MODEL_BASE_URL", "").strip()
            model = payload.get("model") or os.environ.get("MODEL_NAME", "").strip()

            client = MetaModelClient(
                api_key=api_key or None,
                base_url=base_url or None,
                model=model or None,
            )
            result = client.test_connection()
            status_code = HTTPStatus.OK if result.get("connected") else HTTPStatus.OK
            self._send_json(result, status=status_code)
            return

        if path == "/api/set-key":
            content_length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_length)
            try:
                payload = json.loads(body_bytes.decode("utf-8"))
            except Exception as e:
                self._send_json(
                    {"error": f"Invalid JSON payload: {e}"}, status=HTTPStatus.BAD_REQUEST
                )
                return

            new_key = payload.get("api_key", "").strip()
            new_base_url = payload.get("base_url", "").strip()
            new_model = payload.get("model", "").strip()

            if new_key:
                os.environ["MODEL_API_KEY"] = new_key
                if new_base_url:
                    os.environ["MODEL_BASE_URL"] = new_base_url
                if new_model:
                    os.environ["MODEL_NAME"] = new_model

                try:
                    dotenv_file = BASE_DIR / ".env"
                    env_lines = [f"MODEL_API_KEY={new_key}\n"]
                    if new_base_url:
                        env_lines.append(f"MODEL_BASE_URL={new_base_url}\n")
                    if new_model:
                        env_lines.append(f"MODEL_NAME={new_model}\n")
                    dotenv_file.write_text("".join(env_lines), encoding="utf-8")
                except Exception:
                    pass
                self._send_json(
                    {
                        "status": "ok",
                        "message": (
                            f"Model configuration updated! Active: {new_model or 'muse-spark-1.3'}"
                        ),
                        "model": new_model or "muse-spark-1.3",
                    }
                )
            else:
                self._send_json(
                    {"error": "Empty API key provided"}, status=HTTPStatus.BAD_REQUEST
                )
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Path not found")


def run_server(port: int = 8000, host: str = "127.0.0.1") -> None:
    """Start the ArdhiCheck application server."""
    server_address = (host, port)
    httpd = ThreadingHTTPServer(server_address, ArdhiCheckHandler)
    print("\n=======================================================")
    print("  ArdhiCheck – Kenyan Land Survey Auditor Web App")
    print("  Meta Global AI Developer Hackathon (2026)")
    print(f"  Running at: http://{host}:{port}")
    print("=======================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        httpd.server_close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    run_server(port=port)

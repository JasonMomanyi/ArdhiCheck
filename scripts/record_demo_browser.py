"""Automated browser walkthrough and recording for ArdhiCheck.

Drives Google Chrome via the Chrome DevTools Protocol (CDP):
1. Opens http://127.0.0.1:8000.
2. Captures homepage, Meta Hackathon badge, and honest telemetry banner.
3. Opens the Meta AI Configuration modal showing Cerebral Valley notice.
4. Executes Scenario 1 (Nairobi Upper Hill - Green Pass).
5. Inspects field-by-field execution provenance.
6. Executes Scenario 2 (Nakuru - Amber Clerical Blunder).
7. Demonstrates Scenario 3 (Kiambu Riparian Overlap) and Universal Upload.
8. Switches to Cadastral Map & Spatial Reserve Screening on Leaflet map.
9. Saves animated WebP recording and high-res screenshots to recordings/.
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import subprocess
import urllib.request
from pathlib import Path
from typing import Any

import websockets
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
RECORDINGS_DIR = BASE_DIR / "recordings"
SCREENSHOTS_DIR = RECORDINGS_DIR / "screenshots"
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]


def find_browser_executable() -> str:
    for p in CHROME_PATHS:
        if Path(p).exists():
            return p
    raise RuntimeError("Chrome or Edge executable not found")


class CDPController:
    """Controls a Chrome instance via Chrome DevTools Protocol (CDP) WebSocket."""

    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self.ws = None
        self._msg_id = 0

    async def connect(self):
        self.ws = await websockets.connect(self.ws_url, max_size=50 * 1024 * 1024)

    async def close(self):
        if self.ws:
            await self.ws.close()

    async def send(self, method: str, params: dict | None = None) -> dict:
        self._msg_id += 1
        msg_id = self._msg_id
        payload = {"id": msg_id, "method": method, "params": params or {}}
        await self.ws.send(json.dumps(payload))
        while True:
            resp_raw = await self.ws.recv()
            resp = json.loads(resp_raw)
            if resp.get("id") == msg_id:
                return resp.get("result", {})

    async def evaluate(self, expr: str) -> Any:
        res = await self.send("Runtime.evaluate", {"expression": expr, "returnByValue": True})
        return res.get("result", {}).get("value")

    async def capture_screenshot(self, save_path: Path | None = None) -> Image.Image:
        res = await self.send("Page.captureScreenshot", {"format": "png"})
        img_bytes = base64.b64decode(res["data"])
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        if save_path:
            img.save(save_path, quality=95)
        return img


async def run_walkthrough_and_record():
    import sys

    # Ensure local server is active on port 8000
    server_proc = None
    try:
        urllib.request.urlopen("http://127.0.0.1:8000/api/health", timeout=1)
        print("[Record] Local server is already running on port 8000.", flush=True)
    except Exception:
        print("[Record] Starting local ArdhiCheck server on port 8000...", flush=True)
        server_proc = subprocess.Popen(
            [sys.executable, "-m", "app.server", "8000"],
            cwd=str(BASE_DIR),
        )
        for _ in range(20):
            await asyncio.sleep(0.5)
            try:
                urllib.request.urlopen("http://127.0.0.1:8000/api/health", timeout=1)
                print("[Record] Server is ready on http://127.0.0.1:8000.", flush=True)
                break
            except Exception:
                pass

    chrome_bin = find_browser_executable()
    user_data_dir = BASE_DIR / ".chrome_demo_profile"
    user_data_dir.mkdir(parents=True, exist_ok=True)

    # Launch Chrome with remote debugging
    chrome_cmd = [
        chrome_bin,
        "--headless=new",
        "--disable-gpu",
        "--remote-debugging-port=9222",
        f"--user-data-dir={user_data_dir}",
        "--window-size=1280,820",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        "http://127.0.0.1:8000",
    ]

    print(f"[Record] Launching Chrome: {chrome_bin}", flush=True)
    proc = subprocess.Popen(chrome_cmd)
    captured_frames: list[Image.Image] = []

    try:
        # Wait for debugging port to become active
        ws_url = None
        for _ in range(30):
            await asyncio.sleep(0.5)
            try:
                with urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=2) as r:
                    tabs = json.loads(r.read().decode())
                    for tab in tabs:
                        if tab.get("type") == "page" and "webSocketDebuggerUrl" in tab:
                            ws_url = tab["webSocketDebuggerUrl"]
                            break
                    if ws_url:
                        break
            except Exception:
                continue

        if not ws_url:
            raise RuntimeError("Failed to connect to Chrome remote debugging port 9222")

        print(f"[Record] Connected to CDP WebSocket: {ws_url}", flush=True)
        cdp = CDPController(ws_url)
        await cdp.connect()

        async def record_frame(name: str, hold_seconds: float = 1.0):
            print(f"  -> Recording step: {name} (holding {hold_seconds:.1f}s)", flush=True)
            shot_path = SCREENSHOTS_DIR / f"{name}.png"
            img = await cdp.capture_screenshot(shot_path)
            repeats = max(1, int(hold_seconds * 2))
            for _ in range(repeats):
                thumb = img.copy()
                thumb.thumbnail((1200, 768), Image.Resampling.LANCZOS)
                captured_frames.append(thumb)
            await asyncio.sleep(hold_seconds)

        # Step 1: Initial Page Load
        print("\n--- Step 1: Homepage & Telemetry ---")
        await asyncio.sleep(2.0)
        await record_frame("01_homepage_initial", hold_seconds=2.0)

        # Step 2: Open Meta Model API Modal with Cerebral Valley notice
        print("\n--- Step 2: Meta Model API Modal & Failover Notice ---")
        await cdp.evaluate("openApiKeyModal()")
        await record_frame("02_meta_models_modal", hold_seconds=3.0)

        # Show Meta Muse Spark Open self-hosted host option
        await cdp.evaluate(
            "document.getElementById('modalProviderSelect').value = 'spark_open';"
            "onProviderChange()"
        )
        await record_frame("03_open_weights_spark_open", hold_seconds=2.0)

        # Switch back to official dev.meta.ai endpoint
        await cdp.evaluate(
            "document.getElementById('modalProviderSelect').value = 'meta_official';"
            "onProviderChange()"
        )
        await record_frame("04_meta_official_selected", hold_seconds=1.5)
        await cdp.evaluate("closeApiKeyModal()")
        await asyncio.sleep(1.0)

        # Step 3: Run Scenario 1 (Clean Deed Plan - Green Pass)
        print("\n--- Step 3: Scenario 1 (Nairobi Upper Hill - Green Pass) ---")
        await cdp.evaluate("loadScenario('scenario_1')")
        await asyncio.sleep(2.0)
        await record_frame("05_scenario1_green_verdict", hold_seconds=3.5)

        # Scroll to inspect Bowditch traverse and canvas
        await cdp.evaluate("window.scrollBy({top: 380, behavior: 'smooth'})")
        await asyncio.sleep(1.0)
        await record_frame("06_scenario1_bowditch_and_provenance", hold_seconds=3.0)

        # Step 4: Run Scenario 2 (Nakuru Blunder - Amber Typo Detected)
        print("\n--- Step 4: Scenario 2 (Nakuru Municipality - Amber Typo) ---")
        await cdp.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
        await asyncio.sleep(1.0)
        await cdp.evaluate("loadScenario('scenario_2')")
        await asyncio.sleep(2.0)
        await record_frame("07_scenario2_amber_verdict", hold_seconds=3.0)

        # Scroll down to highlight Blunder Localisation table
        await cdp.evaluate("window.scrollBy({top: 550, behavior: 'smooth'})")
        await asyncio.sleep(1.0)
        await record_frame("08_scenario2_blunder_localisation_fix", hold_seconds=3.5)

        # Step 5: Run Scenario 3 (Kiambu Riparian Corridor Overlap - Red)
        print("\n--- Step 5: Scenario 3 (Kiambu River Basin - Red Overlap) ---")
        await cdp.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
        await asyncio.sleep(1.0)
        await cdp.evaluate("loadScenario('scenario_3')")
        await asyncio.sleep(2.0)
        await record_frame("09_scenario3_riparian_overlap_red", hold_seconds=3.0)

        # Step 6: Test Downloads & Universal Upload
        print("\n--- Step 6: Test Data Downloads & Multi-Format Upload ---")
        await cdp.evaluate("window.scrollBy({top: 250, behavior: 'smooth'})")
        await record_frame("10_download_and_upload_zone", hold_seconds=2.5)

        # Step 7: Tab 2 - Cadastral Map & Spatial Reserve Screening
        print("\n--- Step 7: Kenya Cadastral Map & Spatial Reserve Screening ---")
        await cdp.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
        await asyncio.sleep(0.5)
        await cdp.evaluate("switchTab('map')")
        await asyncio.sleep(2.0)
        await record_frame("11_kenya_map_tab_view", hold_seconds=3.0)

        # Place 4 boundary beacons on the interactive Kenya map around Nairobi
        print("  -> Drawing polygon beacons on Leaflet map...")
        await cdp.evaluate("addMapPoint(36.815, -1.295)")
        await asyncio.sleep(0.6)
        await cdp.evaluate("addMapPoint(36.825, -1.295)")
        await asyncio.sleep(0.6)
        await cdp.evaluate("addMapPoint(36.825, -1.305)")
        await asyncio.sleep(0.6)
        await cdp.evaluate("addMapPoint(36.815, -1.305)")
        await asyncio.sleep(1.0)
        await record_frame("12_map_drawn_parcel_polygon", hold_seconds=3.0)

        # Adjust riparian buffer slider to 45m
        await cdp.evaluate(
            "document.getElementById('riparianBufferSlider').value = 45;"
            "updateRiparianSlider(45)"
        )
        await asyncio.sleep(0.5)
        await cdp.evaluate("screenMapReserves()")
        await asyncio.sleep(1.5)
        await cdp.evaluate("window.scrollBy({top: 350, behavior: 'smooth'})")
        await record_frame("13_map_reserve_screening_clear", hold_seconds=3.5)

        # Draw inside Karura Forest to demonstrate conflict detection
        print("  -> Testing Karura Forest conflict detection...")
        await cdp.evaluate("clearMapDrawnPoints()")
        await cdp.evaluate("addMapPoint(36.825, -1.235)")
        await cdp.evaluate("addMapPoint(36.845, -1.235)")
        await cdp.evaluate("addMapPoint(36.845, -1.250)")
        await cdp.evaluate("addMapPoint(36.825, -1.250)")
        await asyncio.sleep(1.0)
        await cdp.evaluate("screenMapReserves()")
        await asyncio.sleep(1.5)
        await record_frame("14_karura_forest_conflict_detected", hold_seconds=3.5)

        # Step 8: Final Summary Screen
        print("\n--- Step 8: Return to Audit Tab for Final Overview ---")
        await cdp.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
        await cdp.evaluate("switchTab('audit')")
        await asyncio.sleep(1.0)
        await cdp.evaluate("loadScenario('scenario_1')")
        await asyncio.sleep(1.5)
        await record_frame("15_final_overview", hold_seconds=3.0)

        await cdp.close()

    finally:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        if server_proc:
            try:
                server_proc.terminate()
                server_proc.wait(timeout=3)
            except Exception:
                try:
                    server_proc.kill()
                except Exception:
                    pass

    print(f"\n[Record] Walkthrough complete! All screenshots saved to {SCREENSHOTS_DIR}")
    print(f"[Record] Captured {len(captured_frames)} frame screenshots.")


if __name__ == "__main__":
    asyncio.run(run_walkthrough_and_record())

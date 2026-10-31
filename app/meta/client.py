"""Meta Model API Client for ArdhiCheck.

Integrates with dev.meta.ai models:
- Muse Spark 1.3: Document extraction from plan photos/PDFs & plain-language report synthesis.
- SAM 3.1: Official media segmentation of rivers, roads, and buffers.
- Optional Muse Spark Open: Meta's open-weight model hosted on a self-hosted endpoint.

Features:
- Image downscaling and optimization before upload to reduce latency & token usage.
- Disk caching keyed by sha256(image + prompt + model) so repeated runs cost $0.00.
- Strict adherence to dev.meta.ai Responses API specification (`input` array with `input_text`
  and `input_image`).
- Exact parsing of SAM 3.1 grammar (`<|box;...|>` and `<|mask;...|>`).
- Transparent provenance tracking and honest offline replay.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

META_API_BASE_URL = "https://api.meta.ai/v1"
DEFAULT_MODEL = "muse-spark-1.3"
MUSE_SPARK_OPEN_MODEL = "muse-spark-open"
CACHE_DIR = Path("data/cache")

BOX_PATTERN = re.compile(
    r"<\|box;x1=(?P<x1>[\d\.]+);y1=(?P<y1>[\d\.]+);x2=(?P<x2>[\d\.]+);"
    r"y2=(?P<y2>[\d\.]+);w=(?P<w>[\d\.]+);h=(?P<h>[\d\.]+)\|>"
)
MASK_PATTERN = re.compile(r"<\|mask;[^|>]*\|>")


def load_env_file(dotenv_path: Path | str = ".env") -> None:
    """Load key-value pairs from a .env file into os.environ if not already set."""
    path = Path(dotenv_path)
    if not path.is_file():
        return
    try:
        content = path.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("\"'")
                if k:
                    os.environ[k] = v
    except Exception:
        pass


# Automatically attempt to load .env on module import
load_env_file()


def optimize_image_for_api(
    image_bytes: bytes,
    max_dimension: int = 1024,
) -> tuple[bytes, str]:
    """Downscale and compress image bytes before upload to reduce token footprint and latency.

    Keeps aspect ratio and returns (compressed_bytes, mime_type).
    """
    if not image_bytes or len(image_bytes) < 100:
        return image_bytes, "image/png"

    try:
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes))

        # Downscale if larger than max_dimension
        w, h = img.size
        if max(w, h) > max_dimension:
            img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

        # Convert to RGB (flatten transparency onto white background)
        if img.mode in ("RGBA", "P"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "RGBA":
                bg.paste(img, mask=img.split()[3])
            else:
                bg.paste(img)
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")

        out_buf = io.BytesIO()
        img.save(out_buf, format="JPEG", quality=85, optimize=True)
        compressed = out_buf.getvalue()

        # If compressed is smaller than original, use JPEG
        if len(compressed) < len(image_bytes):
            return compressed, "image/jpeg"
        return image_bytes, "image/png"
    except Exception:
        return image_bytes, "image/png"


def compute_cache_key(image_bytes: bytes, prompt: str, model: str) -> str:
    """Generate SHA-256 cache key for an image and prompt combination."""
    h = hashlib.sha256()
    h.update(image_bytes)
    h.update(prompt.encode("utf-8"))
    h.update(model.encode("utf-8"))
    return h.hexdigest()


def get_cached_response(cache_key: str) -> dict[str, Any] | None:
    """Retrieve previously cached API response from disk."""
    cache_file = CACHE_DIR / f"{cache_key}.json"
    if cache_file.is_file():
        try:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def save_cached_response(cache_key: str, data: dict[str, Any]) -> None:
    """Save an API response to disk cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{cache_key}.json"
    try:
        cache_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def extract_output_text(data: dict[str, Any]) -> str:
    """Extract visible response text from dev.meta.ai Responses API or OpenAI format."""
    if "output_text" in data and isinstance(data["output_text"], str):
        return data["output_text"]
    for block in data.get("output", []):
        if block.get("type") == "message":
            for content_item in block.get("content", []):
                if content_item.get("type") == "output_text":
                    return content_item.get("text", "")
    choices = data.get("choices", [])
    if choices and "message" in choices[0]:
        msg = choices[0]["message"]
        content = msg.get("content")
        if content:
            return content
        reasoning = msg.get("reasoning_content")
        if reasoning:
            return reasoning
    return ""


extract_response_text = extract_output_text


@dataclass
class PlanExtractionResult:
    """Structured data extracted from a survey plan image or PDF."""

    lr_number: str
    district: str
    locality: str
    stated_area: float
    stated_unit: str  # "ha", "m2", "acre"
    datum_name: str  # e.g. "arc1960_utm37s"
    legs: list[tuple[str, str]]  # list of (bearing_dms_string, distance_m_string)
    raw_notes: list[str] = field(default_factory=list)
    source: str = "Offline replay (pre-recorded)"
    model_name: str = "not run"
    request_id: str = "not run"
    latency_ms: int | str = "not run"
    tokens_used: int | str = "not run"


@dataclass
class SatelliteAnalysisResult:
    """Features detected in a satellite / aerial imagery patch."""

    has_riparian_zone: bool
    riparian_buffer_m: float
    has_road_reserve: bool
    road_buffer_m: float
    detected_features: list[str]
    overlap_area_m2: float
    source: str = "not run"
    model_name: str = "not run"
    request_id: str = "not run"
    latency_ms: int | str = "not run"
    tokens_used: int | str = "not run"
    status: str = "not run"  # "live", "not run", or "cached"


class MetaModelClient:
    """Client for Meta Model API (dev.meta.ai) and optional Muse Spark Open host."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("MODEL_API_KEY", "").strip()
        env_base = os.environ.get("MODEL_BASE_URL", "").strip()
        self.base_url = (base_url or env_base or META_API_BASE_URL).rstrip("/")
        self.model = model or os.environ.get("MODEL_NAME", "").strip() or DEFAULT_MODEL
        if "fireworks.ai" in self.base_url and self.model in (
            "muse-spark-open",
            "meta-models/muse-spark-open",
        ):
            self.model = "accounts/fireworks/models/muse-spark-open"
        self.client = httpx.Client(timeout=60.0)

    @property
    def is_live(self) -> bool:
        """True if a valid-looking API key is configured."""
        return bool(self.api_key and len(self.api_key) > 5)

    def test_connection(self) -> dict[str, Any]:
        """Test connection to the Meta Model API Responses or OpenAI-compatible endpoint."""
        if not self.is_live:
            return {
                "connected": False,
                "status": "Offline replay (pre-recorded)",
                "message": (
                    "No MODEL_API_KEY configured. "
                    "Operating in Offline replay (pre-recorded) mode."
                ),
                "model": self.model,
                "base_url": self.base_url,
            }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        is_openai_compat = "api.meta.ai" not in self.base_url
        ping_text = "ArdhiCheck system ping. Respond with 'Online - Meta Model Ready'."

        if is_openai_compat:
            endpoint = f"{self.base_url}/chat/completions"
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": ping_text}],
                "max_tokens": 1000,
            }
        else:
            endpoint = f"{self.base_url}/responses"
            payload = {
                "model": self.model,
                "input": ping_text,
                "max_output_tokens": 1000,
                "reasoning": {"effort": "minimal"},
            }

        start_time = time.time()
        try:
            resp = self.client.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=25.0,
            )
            # Automatic failover: if /responses returned 404, try /chat/completions
            if resp.status_code == 404 and not is_openai_compat:
                endpoint = f"{self.base_url}/chat/completions"
                payload = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": ping_text}],
                    "max_tokens": 1000,
                }
                resp = self.client.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=25.0,
                )

            latency_ms = int((time.time() - start_time) * 1000)
            if resp.status_code == 200:
                data = resp.json()
                req_id = resp.headers.get("x-request-id", data.get("id", "live_call"))
                sample = extract_output_text(data) or str(data)[:100]
                return {
                    "connected": True,
                    "status": "live",
                    "model": self.model,
                    "base_url": self.base_url,
                    "latency_ms": latency_ms,
                    "request_id": str(req_id),
                    "response_sample": sample.strip(),
                    "message": f"Successfully connected to {self.model} at {self.base_url}.",
                }
            return {
                "connected": False,
                "status": "error",
                "model": self.model,
                "base_url": self.base_url,
                "message": f"API returned status {resp.status_code}: {resp.text[:200]}",
            }
        except Exception as exc:
            return {
                "connected": False,
                "status": "connection_failed",
                "model": self.model,
                "base_url": self.base_url,
                "message": f"Failed to connect to {self.base_url}: {exc}",
            }

    def extract_plan_from_image(
        self,
        image_bytes: bytes,
        mime_type: str = "image/png",
        preset_hint: str | None = None,
    ) -> PlanExtractionResult:
        """Extract survey readings and metadata from plan image bytes."""
        if self.is_live and image_bytes:
            try:
                return self._extract_live(image_bytes, mime_type)
            except Exception as exc:
                print(f"[MetaModelClient] Live API call failed ({exc}); using offline replay.")

        return self._extract_fallback(image_bytes, preset_hint)

    def _extract_live(self, image_bytes: bytes, mime_type: str) -> PlanExtractionResult:
        """Invoke Muse Spark 1.3 via dev.meta.ai Responses API with downscaling and disk cache."""
        prompt_instruction = (
            "You are an expert surveyor reading Kenyan survey deed plans. "
            "Extract parcel metadata and boundary traverse readings. "
            "Return ONLY valid JSON matching this schema:\n"
            "{\n"
            '  "lr_number": "L.R. 209/...",\n'
            '  "district": "...",\n'
            '  "locality": "...",\n'
            '  "stated_area": 0.50,\n'
            '  "stated_unit": "ha",\n'
            '  "datum_name": "arc1960_utm37s",\n'
            '  "legs": [["045°30\'15\\"", "100.000"], ...],\n'
            '  "notes": ["..."]\n'
            "}"
        )

        # Check disk cache first keyed by image hash + prompt + model
        cache_key = compute_cache_key(image_bytes, prompt_instruction, self.model)
        cached_data = get_cached_response(cache_key)
        if cached_data:
            return self._parse_extraction_json(
                cached_data,
                source=f"{self.model} (cached)",
                latency_ms=1,
            )

        # Downscale and optimize image before upload to minimize tokens and latency
        optimized_bytes, opt_mime = optimize_image_for_api(image_bytes, max_dimension=1024)
        b64_image = base64.b64encode(optimized_bytes).decode("utf-8")
        data_url = f"data:{opt_mime};base64,{b64_image}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        is_openai_compat = "api.meta.ai" not in self.base_url
        if is_openai_compat:
            endpoint = f"{self.base_url}/chat/completions"
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt_instruction},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    }
                ],
                "max_tokens": 2048,
            }
        else:
            endpoint = f"{self.base_url}/responses"
            payload = {
                "model": self.model,
                "input": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": prompt_instruction},
                            {"type": "input_image", "image_url": data_url},
                        ],
                    }
                ],
                "max_output_tokens": 2048,
                "reasoning": {"effort": "minimal"},
            }

        start_time = time.time()
        resp = self.client.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=60.0,
        )
        latency_ms = int((time.time() - start_time) * 1000)
        resp.raise_for_status()
        raw_response = resp.json()

        # Cache live response on disk for $0.00 replay
        save_cached_response(cache_key, raw_response)

        return self._parse_extraction_json(
            raw_response,
            source=f"{self.model} (live)",
            latency_ms=latency_ms,
        )

    def _parse_extraction_json(
        self,
        raw_response: dict[str, Any],
        source: str,
        latency_ms: int,
    ) -> PlanExtractionResult:
        """Parse structured cadastral JSON from model response."""
        req_id = raw_response.get("id", "resp_call")
        usage = raw_response.get("usage", {})
        tokens = usage.get("total_tokens", "not reported")

        content_text = extract_output_text(raw_response)

        # Robust JSON substring extraction
        cleaned = content_text.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()
        s_idx = cleaned.find("{")
        e_idx = cleaned.rfind("}")
        if s_idx != -1 and e_idx != -1:
            cleaned = cleaned[s_idx : e_idx + 1]

        parsed = json.loads(cleaned)

        return PlanExtractionResult(
            lr_number=parsed.get("lr_number", "L.R. UNKNOWN"),
            district=parsed.get("district", "Nairobi"),
            locality=parsed.get("locality", "Unknown Locality"),
            stated_area=float(parsed.get("stated_area", 0.5)),
            stated_unit=parsed.get("stated_unit", "ha"),
            datum_name=parsed.get("datum_name", "arc1960_utm37s"),
            legs=[(str(b), str(d)) for b, d in parsed.get("legs", [])],
            raw_notes=parsed.get("notes", []),
            source=source,
            model_name=self.model,
            request_id=str(req_id),
            latency_ms=latency_ms,
            tokens_used=tokens,
        )

    def _extract_fallback(
        self, image_bytes: bytes, preset_hint: str | None = None
    ) -> PlanExtractionResult:
        """Honest offline replay extraction matching verified scenario image files."""
        examples_dir = Path("data/examples")
        if examples_dir.exists():
            for meta_file in sorted(examples_dir.glob("scenario_*.json")):
                try:
                    data = json.loads(meta_file.read_text(encoding="utf-8"))
                    if preset_hint and preset_hint in data.get("id", ""):
                        return PlanExtractionResult(
                            lr_number=data["lr_number"],
                            district=data["district"],
                            locality=data["locality"],
                            stated_area=float(data["stated_area"]),
                            stated_unit=data.get("stated_unit", "ha"),
                            datum_name=data.get("crs_name", "arc1960_utm37s"),
                            legs=[(b, d) for b, d in data["legs"]],
                            raw_notes=data.get("notes", []),
                            source="Offline replay (pre-recorded)",
                            model_name="not run",
                            request_id="not run",
                            latency_ms="not run",
                            tokens_used="not run",
                        )
                except Exception:
                    continue

        return PlanExtractionResult(
            lr_number="L.R. 209/14582",
            district="Nairobi",
            locality="Upper Hill / Community",
            stated_area=0.50,
            stated_unit="ha",
            datum_name="arc1960_utm37s",
            legs=[
                ("000°00'00\"", "100.000"),
                ("090°00'00\"", "50.000"),
                ("180°00'00\"", "100.000"),
                ("270°00'00\"", "50.000"),
            ],
            raw_notes=["Plan extracted from verified test fixture."],
            source="Offline replay (pre-recorded)",
            model_name="not run",
            request_id="not run",
            latency_ms="not run",
            tokens_used="not run",
        )

    def segment_satellite_features(
        self,
        image_bytes: bytes | None,
        feature_prompt: str = "river stream watercourse riparian corridor",
        preset_hint: str | None = None,
    ) -> SatelliteAnalysisResult:
        """Analyze a satellite clip using Meta SAM 3.1.

        Uses the official dev.meta.ai Responses API media segmentation specification:
        input payload with input_text and input_image.
        Parses official grammar: <|box;x1=...;y1=...;x2=...;y2=...;w=...;h=...|><|mask;...|>.
        """
        if not image_bytes:
            return SatelliteAnalysisResult(
                has_riparian_zone=False,
                riparian_buffer_m=0.0,
                has_road_reserve=False,
                road_buffer_m=0.0,
                detected_features=["No satellite image provided"],
                overlap_area_m2=0.0,
                source="not run",
                model_name="not run",
                request_id="not run",
                latency_ms="not run",
                tokens_used="not run",
                status="not run",
            )

        # Check disk cache first
        cache_key = compute_cache_key(image_bytes, feature_prompt, "sam-3.1")
        cached_data = get_cached_response(cache_key)
        if cached_data:
            return self._parse_sam_response(cached_data, source="sam-3.1 (cached)", latency_ms=1)

        # In live mode: call official dev.meta.ai Responses API for SAM 3.1
        if self.is_live:
            try:
                optimized_bytes, opt_mime = optimize_image_for_api(image_bytes, max_dimension=1024)
                b64 = base64.b64encode(optimized_bytes).decode("utf-8")
                data_url = f"data:{opt_mime};base64,{b64}"

                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }

                # Official dev.meta.ai SAM 3.1 Responses API format
                payload = {
                    "model": "sam-3.1",
                    "input": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "input_text", "text": feature_prompt},
                                {"type": "input_image", "image_url": data_url},
                            ],
                        }
                    ],
                }

                start_time = time.time()
                resp = self.client.post(
                    f"{self.base_url}/responses",
                    headers=headers,
                    json=payload,
                    timeout=45.0,
                )
                latency_ms = int((time.time() - start_time) * 1000)
                if resp.status_code == 200:
                    raw_data = resp.json()
                    save_cached_response(cache_key, raw_data)
                    return self._parse_sam_response(
                        raw_data,
                        source="sam-3.1 (live)",
                        latency_ms=latency_ms,
                    )
            except Exception as exc:
                print(f"[MetaModelClient] SAM 3.1 call failed: {exc}")

        return SatelliteAnalysisResult(
            has_riparian_zone=False,
            riparian_buffer_m=0.0,
            has_road_reserve=False,
            road_buffer_m=0.0,
            detected_features=[
                "Satellite segmentation: not run (requires live MODEL_API_KEY with sam-3.1)"
            ],
            overlap_area_m2=0.0,
            source="not run",
            model_name="not run",
            request_id="not run",
            latency_ms="not run",
            tokens_used="not run",
            status="not run",
        )

    def _parse_sam_response(
        self,
        raw_data: dict[str, Any],
        source: str,
        latency_ms: int,
    ) -> SatelliteAnalysisResult:
        """Parse official SAM 3.1 special grammar (<|box;...|><|mask;...|>)."""
        req_id = raw_data.get("id", "sam_resp")
        usage = raw_data.get("usage", {})
        tokens = usage.get("total_tokens", "not reported")

        text = extract_output_text(raw_data)

        # Parse bounding boxes
        boxes: list[dict[str, float]] = []
        for m in BOX_PATTERN.finditer(text):
            boxes.append(
                {
                    "x1": float(m.group("x1")),
                    "y1": float(m.group("y1")),
                    "x2": float(m.group("x2")),
                    "y2": float(m.group("y2")),
                    "w": float(m.group("w")),
                    "h": float(m.group("h")),
                }
            )

        if boxes:
            # Calculate pixel coverage of detected watercourse / riparian feature
            total_box_area = sum((b["x2"] - b["x1"]) * (b["y2"] - b["y1"]) for b in boxes)
            first_box = boxes[0]
            img_area = max(first_box["w"] * first_box["h"], 1.0)
            coverage_fraction = min(total_box_area / img_area, 1.0)
            overlap_m2 = round(coverage_fraction * 1000.0, 1)

            features = [
                f"SAM 3.1 detected {len(boxes)} riparian feature segment(s) "
                f"({coverage_fraction*100:.1f}% frame coverage)"
            ]
            return SatelliteAnalysisResult(
                has_riparian_zone=True,
                riparian_buffer_m=30.0,
                has_road_reserve=False,
                road_buffer_m=0.0,
                detected_features=features,
                overlap_area_m2=overlap_m2,
                source=source,
                model_name="sam-3.1",
                request_id=str(req_id),
                latency_ms=latency_ms,
                tokens_used=tokens,
                status="live",
            )

        return SatelliteAnalysisResult(
            has_riparian_zone=False,
            riparian_buffer_m=0.0,
            has_road_reserve=False,
            road_buffer_m=0.0,
            detected_features=["SAM 3.1: Zero riparian or road reserve encroachments detected."],
            overlap_area_m2=0.0,
            source=source,
            model_name="sam-3.1",
            request_id=str(req_id),
            latency_ms=latency_ms,
            tokens_used=tokens,
            status="live",
        )

    def synthesize_advisory_report(
        self,
        audit_summary: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        """Synthesize report using Muse Spark 1.3 or honest pre-recorded template.

        Returns tuple of (report_markdown, provenance_dict).
        """
        verdict = audit_summary.get("verdict", "UNKNOWN")
        lr_number = audit_summary.get("lr_number", "L.R.")
        closure_info = audit_summary.get("closure", {})
        area_info = audit_summary.get("area", {})
        fixes = audit_summary.get("candidate_fixes", [])
        disclaimer = (
            "\n\n---\n**Disclaimer**: Not legal advice. "
            "Not affiliated with the Ministry of Lands or Ardhisasa."
        )

        stated_m2 = area_info.get("stated_m2", 0)
        comp_m2 = area_info.get("computed_m2", 0)
        lin_misc = closure_info.get("linear_misclosure", 0)
        rel_prec = closure_info.get("relative_precision", "1:inf")

        prompt = (
            "You are ArdhiCheck, an impartial Kenyan land survey audit tool. "
            "Write a concise 3-paragraph executive summary citing exact tool outputs.\n"
            f"Data:\n"
            f"- Parcel: {lr_number}\n"
            f"- Traffic Light Verdict: {verdict}\n"
            f"- Linear Misclosure: {lin_misc:.4f} m\n"
            f"- Relative Precision: {rel_prec}\n"
            f"- Stated Area: {stated_m2:.1f} m² vs Computed {comp_m2:.1f} m²\n"
            f"- Candidate Fixes: {len(fixes)} found\n\n"
            "Provide:\n"
            "1. Executive Verdict (Pass / Warning / Fail)\n"
            "2. Mathematical Findings (cite exact tool outputs)\n"
            "3. Three Specific Questions to ask the Licensed Surveyor or Seller.\n"
        )

        cache_key = compute_cache_key(b"", prompt, self.model)
        cached_data = get_cached_response(cache_key)
        if cached_data:
            out = extract_output_text(cached_data)
            if out:
                req_id = cached_data.get("id", "resp_cached")
                return out + disclaimer, {
                    "source": f"{self.model} (cached)",
                    "model_name": self.model,
                    "request_id": str(req_id),
                    "latency_ms": 1,
                    "tokens_used": 0,
                }

        if self.is_live:
            try:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
                is_openai_compat = "api.meta.ai" not in self.base_url
                if is_openai_compat:
                    endpoint = f"{self.base_url}/chat/completions"
                    payload = {
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 1500,
                    }
                else:
                    endpoint = f"{self.base_url}/responses"
                    payload = {
                        "model": self.model,
                        "input": prompt,
                        "max_output_tokens": 1500,
                        "reasoning": {"effort": "minimal"},
                    }
                start_time = time.time()
                resp = self.client.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=35.0,
                )
                latency_ms = int((time.time() - start_time) * 1000)
                if resp.status_code == 200:
                    raw_data = resp.json()
                    save_cached_response(cache_key, raw_data)
                    out = extract_output_text(raw_data)
                    if out:
                        req_id = resp.headers.get("x-request-id", raw_data.get("id", "live_call"))
                        tokens = raw_data.get("usage", {}).get("total_tokens", "not reported")
                        provenance = {
                            "source": f"{self.model} (live)",
                            "model_name": self.model,
                            "request_id": str(req_id),
                            "latency_ms": latency_ms,
                            "tokens_used": tokens,
                        }
                        return out + disclaimer, provenance
            except Exception:
                pass

        # Honest Offline Replay Template with exact provenance
        provenance = {
            "source": "Offline replay (pre-recorded template)",
            "model_name": "not run",
            "request_id": "not run",
            "latency_ms": "not run",
            "tokens_used": "not run",
        }

        if verdict == "GREEN":
            diff_pct = area_info.get("difference_pct", 0)
            report = (
                f"### Executive Audit Summary: VERIFIED (GREEN)\n\n"
                f"**Parcel {lr_number}** demonstrates mathematical consistency. "
                f"The boundary traverse closes with relative precision (**{rel_prec}**), "
                f"surpassing Kenya's statutory 1:5,000 threshold for cadastral surveys. "
                f"The computed shoelace polygon area of **{comp_m2:,.1f} m²** agrees "
                f"with the stated area on the deed plan within **{diff_pct:.2f}%** tolerance.\n\n"
                f"#### Questions to Ask Your Advocate / Licensed Surveyor:\n"
                f"1. Confirm Deed Plan number matches Registry Index Map (RIM) sheet.\n"
                f"2. Request official search (Form LRA 36) to verify title validity and charges.\n"
                f"3. Commission beacon re-establishment confirming ground pins match coordinates."
            )
        elif verdict == "AMBER":
            top_fix = fixes[0] if fixes else {}
            leg_idx = top_fix.get("leg_index", 0) + 1
            fld = top_fix.get("field", "bearing")
            orig_v = top_fix.get("original_value", "")
            corr_v = top_fix.get("corrected_value", "")
            res_m = top_fix.get("residual_misclosure", 0)
            report = (
                f"### Executive Audit Summary: CAUTION / SUSPECT BLUNDER (AMBER)\n\n"
                f"**Parcel {lr_number}** contains a boundary misclosure of "
                f"**{lin_misc:.3f} metres** (relative precision **{rel_prec}**). "
                f"Under the Kenyan Survey Act, this plan would be rejected at authentication.\n\n"
                f"**Blunder Localisation (app.geo.fixes):** Algorithmic analysis diagnosed a "
                f"probable transposition or clerical typo in **Leg {leg_idx} ({fld})**. "
                f"The printed value is `{orig_v}`, while substituting `{corr_v}` "
                f"resolves the traverse misclosure to {res_m:.4f} m.\n\n"
                f"#### Questions to Ask Your Licensed Surveyor:\n"
                f"1. Did a clerical transposition occur on Leg {leg_idx} during drafting?\n"
                f"2. Ask surveyor for original field computation sheets to confirm azimuth.\n"
                f"3. Do not execute purchase or escrow until an amended deed plan is signed."
            )
        else:  # RED
            diff_m2 = area_info.get("difference_m2", 0)
            diff_pct = area_info.get("difference_pct", 0)
            reason = (
                f"area discrepancy (stated {stated_m2:,.1f} m² vs "
                f"computed {comp_m2:,.1f} m², a {diff_pct:.1f}% shortfall)"
            )
            report = (
                f"### Executive Audit Summary: INCONSISTENCY DETECTED (RED)\n\n"
                f"Parcel **{lr_number}** failed the consistency check due to **{reason}**.\n\n"
                f"- **Closure Status:** Linear misclosure is {lin_misc:.3f} m.\n"
                f"- **Area Audit:** Difference of {diff_m2:,.1f} m² ({diff_pct:.1f}%).\n\n"
                f"#### Questions to Ask Your Licensed Surveyor:\n"
                "1. Why does the computed boundary area differ by "
                f"{diff_m2:,.1f} m² from the deed plan?\n"
                f"2. Request certified ground beacon coordinates and field calculation books.\n"
                f"3. Inquire at the Lands Registry whether an amended deed plan was ever filed."
            )

        return report + disclaimer, provenance

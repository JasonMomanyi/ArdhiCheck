"""Meta Model API Client for ArdhiCheck.

Integrates with dev.meta.ai models:
- Muse Spark 1.3: Document extraction from plan photos/PDFs & plain-language report synthesis.
- SAM 3.1: Zero-shot satellite segmentation of rivers, roads, and buffers.
- Optional Muse Spark Open: Meta's open-weight model hosted on a self-hosted endpoint.

Supports:
1. Live calls to https://api.meta.ai/v1 when MODEL_API_KEY is configured.
2. Honest 'Offline replay (pre-recorded)' mode when MODEL_API_KEY is not set,
   recording exact provenance on every result field.
"""

from __future__ import annotations

import base64
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

META_API_BASE_URL = "https://api.meta.ai/v1"
DEFAULT_MODEL = "muse-spark-1.3"
MUSE_SPARK_OPEN_MODEL = "muse-spark-open"


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
                if k and k not in os.environ:
                    os.environ[k] = v
    except Exception:
        pass


# Automatically attempt to load .env on module import
load_env_file()


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
    status: str = "not run"  # "live", "not run", or "not implemented"


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
        self.client = httpx.Client(timeout=60.0)

    @property
    def is_live(self) -> bool:
        """True if a valid-looking API key is configured."""
        return bool(self.api_key and len(self.api_key) > 5)

    def test_connection(self) -> dict[str, Any]:
        """Test connection to the Meta Model API Responses endpoint."""
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
        payload = {
            "model": self.model,
            "input": "ArdhiCheck system ping. Respond with 'Online - Meta Model Ready'.",
        }
        start_time = time.time()
        try:
            resp = self.client.post(
                f"{self.base_url}/responses",
                headers=headers,
                json=payload,
                timeout=15.0,
            )
            latency_ms = int((time.time() - start_time) * 1000)
            if resp.status_code == 200:
                data = resp.json()
                req_id = resp.headers.get("x-request-id", data.get("id", "live_call"))
                sample = data.get("output_text") or str(data)[:100]
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
        if self.is_live:
            try:
                return self._extract_live(image_bytes, mime_type)
            except Exception as exc:
                print(f"[MetaModelClient] Live API call failed ({exc}); using offline replay.")

        return self._extract_fallback(image_bytes, preset_hint)

    def _extract_live(self, image_bytes: bytes, mime_type: str) -> PlanExtractionResult:
        """Invoke Muse Spark 1.3 via Responses API with image input."""
        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        data_url = f"data:{mime_type};base64,{b64_image}"

        system_instruction = (
            "You are an expert surveyor reading Kenyan survey deed plans. "
            "Extract parcel metadata and boundary traverse readings. "
            "Return valid JSON matching this structure:\n"
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

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "input": [
                {"role": "system", "content": system_instruction},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Extract all boundary traverse readings "
                                "from this survey plan."
                            ),
                        },
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
            "response_format": {"type": "json_object"},
        }

        start_time = time.time()
        resp = self.client.post(f"{self.base_url}/responses", headers=headers, json=payload)
        latency_ms = int((time.time() - start_time) * 1000)
        resp.raise_for_status()
        data = resp.json()

        req_id = resp.headers.get("x-request-id", data.get("id", "live_call"))
        tokens = data.get("usage", {}).get("total_tokens", "not reported")

        content_text = data.get("output_text") or data.get("choices", [{}])[0].get(
            "message", {}
        ).get("content", "{}")

        # Parse JSON robustly
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
            source=f"{self.model} (live)",
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

        # Standard default fixture for manual uploads when offline
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
        feature_prompt: str = "river stream watercourse road reserve",
        preset_hint: str | None = None,
    ) -> SatelliteAnalysisResult:
        """Analyze a satellite clip using Meta SAM 3.1.

        Uses the official dev.meta.ai Responses API media segmentation specification.
        When not connected or not run, reports 'not run' with zero hard-coded numbers.
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

        # In live mode: attempt real SAM 3.1 media segmentation call per dev.meta.ai spec
        if self.is_live:
            try:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
                b64 = base64.b64encode(image_bytes).decode("utf-8")
                payload = {
                    "model": "sam-3.1",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "input_text", "text": feature_prompt},
                                {
                                    "type": "input_image",
                                    "image_url": {"url": f"data:image/png;base64,{b64}"},
                                },
                            ],
                        }
                    ],
                    "metadata": {"include_confidence": "true"},
                }
                start_time = time.time()
                resp = self.client.post(
                    f"{self.base_url}/responses",
                    headers=headers,
                    json=payload,
                    timeout=30.0,
                )
                latency_ms = int((time.time() - start_time) * 1000)
                if resp.status_code == 200:
                    data = resp.json()
                    req_id = resp.headers.get("x-request-id", data.get("id", "live_call"))
                    tokens = data.get("usage", {}).get("total_tokens", "not reported")
                    overlap = float(data.get("overlap_area_m2", 0.0))
                    feats = data.get("features", ["SAM 3.1 segment returned"])
                    return SatelliteAnalysisResult(
                        has_riparian_zone=overlap > 0,
                        riparian_buffer_m=30.0 if overlap > 0 else 0.0,
                        has_road_reserve=False,
                        road_buffer_m=0.0,
                        detected_features=feats,
                        overlap_area_m2=overlap,
                        source="sam-3.1 (live)",
                        model_name="sam-3.1",
                        request_id=str(req_id),
                        latency_ms=latency_ms,
                        tokens_used=tokens,
                        status="live",
                    )
            except Exception as exc:
                print(f"[MetaModelClient] SAM 3.1 call failed: {exc}")

        # When offline or unconfigured: report honestly that satellite analysis was not run.
        # No fabricated encroachment numbers or fake confidence scores.
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

        if self.is_live:
            try:
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
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
                start_time = time.time()
                resp = self.client.post(
                    f"{self.base_url}/responses",
                    headers=headers,
                    json={"model": self.model, "input": prompt},
                    timeout=30.0,
                )
                latency_ms = int((time.time() - start_time) * 1000)
                if resp.status_code == 200:
                    data = resp.json()
                    out = data.get("output_text") or data.get("choices", [{}])[0].get(
                        "message", {}
                    ).get("content")
                    if out:
                        req_id = resp.headers.get("x-request-id", data.get("id", "live_call"))
                        tokens = data.get("usage", {}).get("total_tokens", "not reported")
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

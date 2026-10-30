"""Tests for replaying saved live fixtures and live Meta Model API tests."""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.meta.client import MetaModelClient
from app.pipeline import run_survey_audit

FIXTURES_DIR = Path("tests/fixtures/live")


def test_replay_saved_spark_fixture() -> None:
    """Verify that replaying the real dev.meta.ai live response passes the full pipeline."""
    spark_fixture_path = FIXTURES_DIR / "spark_response.json"
    assert spark_fixture_path.is_file(), "Saved live spark fixture missing"

    raw_response = json.loads(spark_fixture_path.read_text(encoding="utf-8"))

    # Mock client httpx response to return saved live JSON
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = raw_response
    mock_resp.headers = {"x-request-id": raw_response.get("id", "live_test_id")}

    client = MetaModelClient(api_key="mock_live_test_key_for_replay")
    client.client.post = MagicMock(return_value=mock_resp)

    # Load plan image bytes
    plan_path = Path("data/examples/scenario_1_clean_plan.png")
    image_bytes = plan_path.read_bytes()

    result = run_survey_audit(plan_image_bytes=image_bytes, meta_client=client)

    assert result["verdict"] == "GREEN"
    assert "209" in result["lr_number"]
    assert result["closure"]["relative_precision"] == "1:inf"
    assert result["area"]["computed_m2"] == 5000.0
    assert result["area"]["within_tolerance"] is True
    assert result["provenance"]["extraction"]["model_name"] == "muse-spark-1.3"
    assert result["provenance"]["geometry"]["source"] == "app.geo (pure Python, 0 tokens)"
    assert "Not legal advice" in result["disclaimer"]


def test_disk_cache_zero_cost_replay() -> None:
    """Verify that disk cache returns cached response without making network requests."""
    plan_path = Path("data/examples/scenario_1_clean_plan.png")
    image_bytes = plan_path.read_bytes()

    client = MetaModelClient(api_key="mock_key")
    # Disallow network calls by mocking post to fail if called
    client.client.post = MagicMock(side_effect=RuntimeError("Network should not be called!"))

    # Extract using image that was cached during the live run
    extraction = client.extract_plan_from_image(image_bytes=image_bytes)

    assert "cached" in extraction.source or "live" in extraction.source
    assert extraction.model_name == "muse-spark-1.3"
    assert len(extraction.legs) == 4
    assert extraction.stated_area == 0.5


@pytest.mark.live
def test_live_meta_api_ping() -> None:
    """Live integration test against dev.meta.ai Responses API.

    Only runs when MODEL_API_KEY is configured in the environment.
    """
    key = os.environ.get("MODEL_API_KEY", "").strip()
    if not key or len(key) < 5 or key == "test_key_update":
        pytest.skip("Valid MODEL_API_KEY environment variable is not configured.")

    client = MetaModelClient(api_key=key)
    res = client.test_connection()
    assert res["connected"] is True, f"Live ping failed: {res.get('message')}"
    assert res["model"] == "muse-spark-1.3"
    assert res["status"] == "live"
    assert res["latency_ms"] > 0

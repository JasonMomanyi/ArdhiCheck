"""Script to execute a live plan extraction and capture fixtures for offline replay."""

import hashlib
import json
from pathlib import Path

from app.meta.client import (
    MetaModelClient,
    load_env_file,
    optimize_image_for_api,
)
from app.pipeline import run_survey_audit

load_env_file()


def main():
    client = MetaModelClient()
    if not client.is_live:
        print("ERROR: MODEL_API_KEY is not set.")
        return

    plan_path = Path("data/examples/scenario_1_clean_plan.png")
    image_bytes = plan_path.read_bytes()
    image_hash = hashlib.sha256(image_bytes).hexdigest()

    opt_bytes, opt_mime = optimize_image_for_api(image_bytes, max_dimension=1024)

    # 1. Capture direct extraction call with raw request & response
    fixtures_dir = Path("tests/fixtures/live")
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    print(f"Original image size: {len(image_bytes)} bytes")
    print(f"Optimized image size: {len(opt_bytes)} bytes ({opt_mime})")
    print("Sending live request to dev.meta.ai...")

    # Run extraction via client (which will call live API and cache response)
    extraction = client.extract_plan_from_image(image_bytes=image_bytes)

    # Find the cached response file for this image
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
    from app.meta.client import compute_cache_key, get_cached_response

    cache_key = compute_cache_key(image_bytes, prompt_instruction, client.model)
    raw_response = get_cached_response(cache_key)

    # Save request metadata (minus secrets)
    request_metadata = {
        "endpoint": f"{client.base_url}/responses",
        "model": client.model,
        "max_output_tokens": 2048,
        "reasoning": {"effort": "minimal"},
        "headers": {
            "Content-Type": "application/json",
            "Authorization": "Bearer [REDACTED_API_KEY]",
        },
        "image_file": str(plan_path),
        "image_sha256": image_hash,
        "original_size_bytes": len(image_bytes),
        "optimized_size_bytes": len(opt_bytes),
        "optimized_mime_type": opt_mime,
        "cache_key": cache_key,
    }

    (fixtures_dir / "request_metadata.json").write_text(
        json.dumps(request_metadata, indent=2), encoding="utf-8"
    )

    if raw_response:
        (fixtures_dir / "spark_response.json").write_text(
            json.dumps(raw_response, indent=2), encoding="utf-8"
        )
        print("Saved spark_response.json to tests/fixtures/live/")

    print("\n--- Live Extraction Result ---")
    print(f"LR Number:   {extraction.lr_number}")
    print(f"Locality:    {extraction.locality}")
    print(f"Stated Area: {extraction.stated_area} {extraction.stated_unit}")
    print(f"Legs:        {extraction.legs}")
    print(f"Source:      {extraction.source}")
    print(f"Latency:     {extraction.latency_ms} ms")
    print(f"Tokens:      {extraction.tokens_used}")

    # 2. Run full pipeline
    print("\nRunning full pipeline through geometry...")
    result = run_survey_audit(plan_image_bytes=image_bytes, meta_client=client)

    # Clean secrets if any before saving
    (fixtures_dir / "audit_result.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print("Saved audit_result.json to tests/fixtures/live/")
    print(f"Pipeline Verdict: {result['verdict']}")
    print(f"Relative Precision: {result['closure']['relative_precision']}")
    print(f"Computed Area: {result['area']['computed_m2']:.1f} m2")


if __name__ == "__main__":
    main()

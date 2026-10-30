"""Spike script – verify Meta Model API access.

Directly targets dev.meta.ai Responses API with model muse-spark-1.3,
or optional self-hosted muse-spark-open endpoint.
Reads credentials from MODEL_API_KEY, MODEL_BASE_URL, and MODEL_NAME (.env or env).
Never logs or prints the API key.

Usage:
    python scripts/spike_meta.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any


def load_dotenv() -> None:
    """Load MODEL_* variables from .env if present."""
    p = Path(".env")
    if p.is_file():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip("\"'")
                if k and k not in os.environ:
                    os.environ[k] = v


def extract_output_text(data: dict[str, Any]) -> str:
    """Extract visible response text from dev.meta.ai Responses API payload."""
    if "output_text" in data and isinstance(data["output_text"], str):
        return data["output_text"]
    for block in data.get("output", []):
        if block.get("type") == "message":
            for content_item in block.get("content", []):
                if content_item.get("type") == "output_text":
                    return content_item.get("text", "")
    choices = data.get("choices", [])
    if choices and "message" in choices[0]:
        return choices[0]["message"].get("content", "")
    return ""


def main() -> None:
    """Make a text-only call to the configured Meta model and print the response."""
    load_dotenv()
    api_key = os.environ.get("MODEL_API_KEY", "").strip()
    base_url = os.environ.get("MODEL_BASE_URL", "https://api.meta.ai/v1").rstrip("/")
    model = os.environ.get("MODEL_NAME", "muse-spark-1.3").strip()

    if not api_key:
        print("ERROR: Set the MODEL_API_KEY environment variable.", file=sys.stderr)
        print("  cp .env.example .env  # edit .env with your dev.meta.ai key", file=sys.stderr)
        sys.exit(1)

    prompt = (
        "What are the three most common coordinate reference systems "
        "used in Kenyan cadastral land surveys? Reply in two sentences."
    )

    import httpx

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "input": prompt,
        "max_output_tokens": 2500,
        "reasoning": {"effort": "minimal"},
    }

    try:
        resp = httpx.post(
            f"{base_url}/responses",
            headers=headers,
            json=payload,
            timeout=40.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            out_text = extract_output_text(data)
            usage = data.get("usage", {})
            print(f"=== {model} – Text Spike (dev.meta.ai Responses API) ===")
            print(f"Base URL: {base_url}")
            print(f"Model:    {model}")
            print(f"Output:   {out_text.strip()}")
            print(f"Usage:    {usage}")
            print("=========================================================")
        else:
            err_msg = resp.text[:300]
            print(f"ERROR: API returned HTTP {resp.status_code}: {err_msg}", file=sys.stderr)
            sys.exit(1)
    except Exception as exc:
        print(f"ERROR: Could not connect to {base_url}: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

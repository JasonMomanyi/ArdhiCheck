"""Spike script – verify Meta Model API access with Muse Spark 1.3.

Uses the OpenAI Python SDK or httpx with the Meta Model API base URL.
Reads the API key from the MODEL_API_KEY environment variable or .env.

Usage:
    python scripts/spike_meta.py

For image understanding and tool-calling spikes, read the official docs first:
  - https://dev.meta.ai/docs/image-understanding
  - https://dev.meta.ai/docs/tool-calling
Do NOT guess request formats; implement only after reading the docs.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def load_dotenv() -> None:
    """Load MODEL_API_KEY from .env if present."""
    p = Path(".env")
    if p.is_file():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip("\"'")
                if k and k not in os.environ:
                    os.environ[k] = v


def main() -> None:
    """Make a text-only call to Muse Spark 1.3 and print the response."""
    load_dotenv()
    api_key = os.environ.get("MODEL_API_KEY")
    if not api_key:
        print("ERROR: Set the MODEL_API_KEY environment variable.", file=sys.stderr)
        print("  cp .env.example .env  # then edit .env", file=sys.stderr)
        sys.exit(1)

    prompt = (
        "What are the three most common coordinate reference systems "
        "used in Kenyan land surveys? Reply in two sentences."
    )

    try:
        from openai import OpenAI

        client = OpenAI(
            base_url="https://api.meta.ai/v1",
            api_key=api_key,
        )
        response = client.responses.create(
            model="muse-spark-1.3",
            input=prompt,
        )
        print("=== Muse Spark 1.3 – Text Spike (OpenAI SDK) ===")
        print(f"Output: {response.output_text}")
        print(f"Usage:  {response.usage}")
        print("================================================")
        return
    except ImportError:
        pass

    # Direct fallback using httpx
    import httpx

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "muse-spark-1.3",
        "input": prompt,
    }
    resp = httpx.post(
        "https://api.meta.ai/v1/responses",
        headers=headers,
        json=payload,
        timeout=30.0,
    )
    if resp.status_code == 200:
        data = resp.json()
        print("=== Muse Spark 1.3 – Text Spike (Direct HTTP) ===")
        print(f"Output: {data.get('output_text')}")
        print(f"Usage:  {data.get('usage')}")
        print("=================================================")
    else:
        print(f"ERROR: API returned HTTP {resp.status_code}: {resp.text}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

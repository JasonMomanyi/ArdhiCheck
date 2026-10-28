"""Spike script – verify Meta Model API access with Muse Spark 1.3.

Uses the OpenAI Python SDK with the Meta Model API base URL.
Reads the API key from the MODEL_API_KEY environment variable.

Usage:
    python scripts/spike_meta.py

For image understanding and tool-calling spikes, read the official docs first:
  - https://dev.meta.ai/docs/image-understanding
  - https://dev.meta.ai/docs/tool-calling
Do NOT guess request formats; implement only after reading the docs.
"""

import os
import sys


def main() -> None:
    """Make a text-only call to Muse Spark 1.3 and print the response."""
    api_key = os.environ.get("MODEL_API_KEY")
    if not api_key:
        print("ERROR: Set the MODEL_API_KEY environment variable.", file=sys.stderr)
        print("  cp .env.example .env  # then edit .env", file=sys.stderr)
        sys.exit(1)

    # Import here so the rest of the repo doesn't require openai at import time
    try:
        from openai import OpenAI
    except ImportError:
        print("ERROR: Install the openai package:  pip install -e '.[meta]'", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(
        base_url="https://api.meta.ai/v1",
        api_key=api_key,
    )

    # Text-only spike using the Responses API
    prompt = (
        "What are the three most common coordinate reference systems "
        "used in Kenyan land surveys? Reply in two sentences."
    )
    response = client.responses.create(
        model="muse-spark-1.3",
        input=prompt,
    )

    print("=== Muse Spark 1.3 – Text Spike ===")
    print(f"Output: {response.output_text}")
    print(f"Usage:  {response.usage}")
    print("====================================")

    # TODO: Image understanding spike (read docs first)
    # TODO: Tool-calling spike (read docs first)


if __name__ == "__main__":
    main()

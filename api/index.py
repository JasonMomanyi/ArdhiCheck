"""Vercel Serverless Python Handler for ArdhiCheck."""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path so app module imports resolve cleanly
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.server import ArdhiCheckHandler  # noqa: E402


class handler(ArdhiCheckHandler):  # noqa: N801
    """Vercel Serverless Function entry point exporting `handler`."""

    pass

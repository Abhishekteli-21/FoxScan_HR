"""Vercel entry point.

Vercel runs each file under api/ as a serverless function and speaks ASGI to
whatever is exported as `app`, so this just re-exports the FastAPI application.
vercel.json rewrites every path here, so the same server handles the UI at /
and the /api/* endpoints — exactly like `uvicorn app.main:app` does locally.
"""

import sys
from pathlib import Path

# The function's working directory is api/, so put the project root on sys.path
# to make `app` (and the knowledge/ + static/ files beside it) importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app  # noqa: E402,F401  (re-exported for Vercel)

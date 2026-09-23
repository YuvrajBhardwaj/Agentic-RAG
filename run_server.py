#!/usr/bin/env python
"""Run the FastAPI server (portable — no hardcoded paths)."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PORT = 8000

sys.exit(subprocess.call([
    sys.executable, "-m", "uvicorn",
    "app.main:app",
    "--host", "0.0.0.0",
    "--port", str(PORT),
    "--reload",
], cwd=str(ROOT)))

#!/usr/bin/env python
"""Run the FastAPI server"""
import subprocess
import sys
import os

os.chdir(r"c:\Users\yuvra\OneDrive\Desktop\Agentic RAG")
sys.exit(subprocess.call([
    sys.executable, "-m", "uvicorn", 
    "app.main:app",
    "--host", "0.0.0.0",
    "--port", "8000",
    "--reload"
]))

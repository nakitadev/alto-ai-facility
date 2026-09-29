"""
Pytest configuration and shared fixtures for AltoTech AI Engineer test suite.
"""

import sys
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Ensure dummy keys for local test execution if not in environment
os.environ.setdefault("OPENROUTER_API_KEY", "test-key")
os.environ.setdefault("DEFAULT_TIMEZONE", "Asia/Bangkok")

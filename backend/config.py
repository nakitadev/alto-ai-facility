import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env", override=True)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# TypeSafe AI / Jev System One Configuration
TYPESAFE_API_KEY = os.getenv("TYPESAFE_API_KEY")

POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT")) if os.getenv("POSTGRES_PORT") else None
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL and POSTGRES_HOST and POSTGRES_PORT:
    DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

BACKEND_HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
# Supports Railway, Cloud Run, Render dynamic PORT env var
port_val = os.getenv("PORT") or os.getenv("BACKEND_PORT")
BACKEND_PORT = int(port_val) if port_val else 8000

DEFAULT_TIMEZONE = os.getenv("DEFAULT_TIMEZONE", "Asia/Bangkok")
DOCS_DIR = ROOT_DIR / "docs"

# Logfire Observability & Tracing Configuration
LOGFIRE_TOKEN = os.getenv("LOGFIRE_TOKEN")
LOGFIRE_SERVICE_NAME = os.getenv("LOGFIRE_SERVICE_NAME", "alto-tech-ai-engineer")

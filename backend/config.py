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
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT"))
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

BACKEND_HOST = os.getenv("BACKEND_HOST")
BACKEND_PORT = int(os.getenv("BACKEND_PORT"))
DEFAULT_TIMEZONE = os.getenv("DEFAULT_TIMEZONE")
DOCS_DIR = ROOT_DIR / "docs"

# Logfire Observability & Tracing Configuration
LOGFIRE_TOKEN = os.getenv("LOGFIRE_TOKEN", None)
LOGFIRE_SERVICE_NAME = os.getenv("LOGFIRE_SERVICE_NAME", "alto-tech-ai-engineer")

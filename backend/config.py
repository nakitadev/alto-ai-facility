from os import getenv
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env", override=True)

LLM_PROVIDER = getenv("LLM_PROVIDER", "openrouter").lower()
OPENROUTER_API_KEY = getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = getenv("OPENROUTER_MODEL", "inclusionai/ling-3.0-flash-sante:free")
OPENROUTER_BASE_URL = getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# Curated list of verified free OpenRouter models supporting tool calling
FREE_OPENROUTER_MODELS = [
    {
        "id": "inclusionai/ling-3.0-flash-sante:free",
        "name": "Ling 3.0 Flash (Default · Ultra-Fast)",
        "context_length": "256k",
        "supports_tools": True
    },
    {
        "id": "nvidia/nemotron-3.5-lightning:free",
        "name": "NVIDIA Nemotron 3.5 Lightning (High Precision)",
        "context_length": "1,000k",
        "supports_tools": True
    },
    {
        "id": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "name": "NVIDIA Nemotron 3 Ultra 550B (Deep Reasoning)",
        "context_length": "1,000k",
        "supports_tools": True
    },
    {
        "id": "google/gemma-4-31b-it:free",
        "name": "Google Gemma 4 31B Instruct",
        "context_length": "262k",
        "supports_tools": True
    },
    {
        "id": "qwen/qwen3.8-27b:free",
        "name": "Qwen 3.8 27B Instruct",
        "context_length": "262k",
        "supports_tools": True
    },
    {
        "id": "openrouter/free",
        "name": "OpenRouter Auto-Free Router",
        "context_length": "200k",
        "supports_tools": True
    }
]

# TypeSafe AI / Jev System One Configuration
TYPESAFE_API_KEY = getenv("TYPESAFE_API_KEY")

POSTGRES_HOST = getenv("POSTGRES_HOST")
POSTGRES_PORT = int(getenv("POSTGRES_PORT")) if getenv("POSTGRES_PORT") else None
POSTGRES_USER = getenv("POSTGRES_USER")
POSTGRES_PASSWORD = getenv("POSTGRES_PASSWORD")
POSTGRES_DB = getenv("POSTGRES_DB")

DATABASE_URL = getenv("DATABASE_URL")
if not DATABASE_URL and POSTGRES_HOST and POSTGRES_PORT:
    DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

BACKEND_HOST = getenv("BACKEND_HOST", "0.0.0.0")
# Supports Railway, Cloud Run, Render dynamic PORT env var
port_val = getenv("PORT") or getenv("BACKEND_PORT")
BACKEND_PORT = int(port_val) if port_val else 8000

DEFAULT_TIMEZONE = getenv("DEFAULT_TIMEZONE", "Asia/Bangkok")
DOCS_DIR = ROOT_DIR / "docs"

# Logfire Observability & Tracing Configuration
LOGFIRE_TOKEN = getenv("LOGFIRE_TOKEN")
LOGFIRE_SERVICE_NAME = getenv("LOGFIRE_SERVICE_NAME", "alto-tech-ai-engineer")

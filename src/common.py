from pathlib import Path
import os
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / '.env')


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f'Missing required environment variable: {name}. Copy .env.example to .env and fill it in.')
    return value


def ensure_parent(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path

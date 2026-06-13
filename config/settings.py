import os
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ── Base Paths ─────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent

# ── Database ───────────────────────────────────────────────────────────────────
DB_PATH = BASE_DIR / os.getenv("DB_PATH", "data/trading_journal.db")

# ── API Keys ───────────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ── Application ────────────────────────────────────────────────────────────────
APP_ENV = os.getenv("APP_ENV", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ── Validation ─────────────────────────────────────────────────────────────────
def validate_config() -> None:

    errors = []
    warnings = []

    # Hard requirements
    if not DB_PATH.parent.exists():
        try:
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            errors.append(f"Cannot create database directory: {e}")

    # Soft requirements — features degrade, app still runs
    if not OPENAI_API_KEY:
        warnings.append(
            "OPENAI_API_KEY not set — AI features will be disabled"
        )

    if APP_ENV not in ("development", "production", "test"):
        warnings.append(
            f"Unknown APP_ENV='{APP_ENV}' — expected development/production/test"
        )

    # Hard fail
    if errors:
        for error in errors:
            print(f"[CONFIG ERROR] {error}")
        raise EnvironmentError(
            f"Configuration errors prevent startup: {errors}"
        )

    # Soft warnings — log them, don't crash
    for warning in warnings:
        # Use print here because logging isn't configured yet
        # when settings.py is first imported
        print(f"[CONFIG WARNING] {warning}")


validate_config()

# ── Database URL ───────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL")

IS_POSTGRES = DATABASE_URL is not None and DATABASE_URL.startswith("postgresql")

def get_database_url() -> str:

    if DATABASE_URL:

        return DATABASE_URL.replace("postgres://", "postgresql://", 1)

    else:

        return f"sqlite:///{DB_PATH}"
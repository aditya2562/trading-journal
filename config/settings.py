import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent

DB_PATH = BASE_DIR / os.getenv("DB_PATH", "data/trading_journal.db")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

APP_ENV = os.getenv("APP_ENV", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

def validate_config():

    if APP_ENV == "production" and not OPENAI_API_KEY:
        raise EnvironmentError(
            "OPENAI_API_KEY is required in production."
            "Add it to your .env file."
        )
        
validate_config()
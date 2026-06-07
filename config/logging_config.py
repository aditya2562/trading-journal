import logging
import logging.handlers
from pathlib import Path
from config.settings import LOG_LEVEL, BASE_DIR

LOG_FILE = BASE_DIR / "logs" / "app.log"

def setup_logging() -> None:

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    numeric_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    if root_logger.handlers:
        root_logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s  %(levelname)-8s  %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)

    file_handler = logging.handlers.RotatingFileHandler(
        filename=str(LOG_FILE),
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5,
        encoding="utf-8",
    )

    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    noisy_loggers = [
        "urllib3",
        "httpx",
        "httpcore",
        "openai",
        "yfinance",
        "peewee",
        "PIL",
        "matplotlib",
    ]
    for name in noisy_loggers:
        logging.getLogger(name).setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging configured — level={LOG_LEVEL} "
        f"file={LOG_FILE}"
    )
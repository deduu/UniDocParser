import logging
from logging.handlers import RotatingFileHandler
import os


def configure_logging():
    os.makedirs("logs", exist_ok=True)
    log_file = "logs/UniDocParser.log"

    # Check if handler is already set (avoid duplicate & open file leaks)
    root_logger = logging.getLogger()
    # --- <— new: strip out any pre-existing handlers so we don’t double-print
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)

    # Create file handler
    handler = RotatingFileHandler(
        log_file, maxBytes=5*1024*1024, backupCount=3)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)

    # Optional: also add console output
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

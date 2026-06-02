import logging
import os

def setup_logging(log_file="trading_bot.log"):
    """
    Sets up a logger that logs DEBUG level messages to a log file
    and INFO level messages to the console.
    """
    logger = logging.getLogger("trading_bot")
    logger.setLevel(logging.DEBUG)

    # Avoid duplicate handlers if setup_logging is called multiple times (e.g., in Streamlit)
    if logger.handlers:
        return logger

    # Log format with timestamp, level, and message
    file_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(asctime)s - [%(levelname)s] - %(message)s',
        datefmt='%H:%M:%S'
    )

    # File handler (logs everything from DEBUG upwards)
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Console handler (logs INFO and above)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger

# Initialize the default logger instance
logger = setup_logging()

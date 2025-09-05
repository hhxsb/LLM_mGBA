"""
Centralized logging configuration for AI GBA Player.
Provides efficient, structured logging with emoji prefixes for clear visual organization.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


class EmojiFormatter(logging.Formatter):
    """Custom formatter that adds emoji prefixes for different log levels."""
    
    LEVEL_EMOJIS = {
        'DEBUG': '🔍',
        'INFO': '📝',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'CRITICAL': '🚨'
    }
    
    def format(self, record):
        emoji = self.LEVEL_EMOJIS.get(record.levelname, '📝')
        record.emoji = emoji
        return super().format(record)


def setup_logging(
    level: int = logging.INFO,
    log_to_file: bool = True,
    log_dir: str = "logs"
) -> logging.Logger:
    """
    Set up centralized logging for the AI GBA Player.
    
    Args:
        level: Logging level (default: INFO)
        log_to_file: Whether to log to file in addition to console
        log_dir: Directory for log files
        
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger('ai_gba_player')
    logger.setLevel(level)
    
    # Avoid adding multiple handlers if already configured
    if logger.handlers:
        return logger
    
    # Console handler with emoji formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = EmojiFormatter(
        '%(emoji)s %(name)s: %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_to_file:
        try:
            log_path = Path(log_dir)
            log_path.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d')
            file_handler = logging.FileHandler(
                log_path / f'ai_gba_player_{timestamp}.log'
            )
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"Could not set up file logging: {e}")
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(f'ai_gba_player.{name}')


# Create default logger instance
default_logger = setup_logging()
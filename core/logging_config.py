"""
Shared logging configuration for AI Pokemon Trainer project.
Provides consistent logging across all processes and components.
"""

import logging
import os
import sys
from typing import Optional


class PokemonAILogger:
    """Centralized logger configuration for the Pokemon AI project."""
    
    _configured = False
    _debug_mode = False
    
    @classmethod
    def configure(cls, debug: bool = False, process_name: str = "main") -> None:
        """Configure logging for the entire project."""
        if cls._configured:
            return
            
        cls._debug_mode = debug
        
        # Check environment variable for debug mode (for child processes)
        if os.getenv('POKEMON_AI_DEBUG') == '1':
            cls._debug_mode = True
            debug = True
        
        # Set up root logger
        root_logger = logging.getLogger('pokemon_ai')
        root_logger.handlers.clear()  # Clear any existing handlers
        
        # Set level based on debug mode
        level = logging.DEBUG if debug else logging.INFO
        root_logger.setLevel(level)
        
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        
        # Create detailed formatter with process identification
        formatter = logging.Formatter(
            fmt='%(asctime)s - [%(process)d:%(processName)s] - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        
        # Add handler to root logger
        root_logger.addHandler(console_handler)
        
        # Prevent duplicate logs
        root_logger.propagate = False
        
        cls._configured = True
        
        # Log configuration complete
        logger = cls.get_logger(f"{process_name}.config")
        logger.info(f"🔧 Logging configured for process '{process_name}' (debug={debug})")
        
        if debug:
            logger.debug("🐛 Debug logging enabled - you will see detailed flow information")
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Get a logger instance with consistent configuration."""
        if not cls._configured:
            # Auto-configure with defaults if not already configured
            cls.configure()
        
        # Ensure the name is under our hierarchy
        if not name.startswith('pokemon_ai.'):
            name = f'pokemon_ai.{name}'
        
        logger = logging.getLogger(name)
        
        # Set level based on current debug mode
        level = logging.DEBUG if cls._debug_mode else logging.INFO
        logger.setLevel(level)
        
        return logger
    
    @classmethod
    def is_debug_enabled(cls) -> bool:
        """Check if debug logging is enabled."""
        return cls._debug_mode
    
    @classmethod
    def set_debug_env_var(cls) -> None:
        """Set environment variable for child processes to inherit debug mode."""
        if cls._debug_mode:
            os.environ['POKEMON_AI_DEBUG'] = '1'
        else:
            os.environ.pop('POKEMON_AI_DEBUG', None)


def get_logger(name: str) -> logging.Logger:
    """Convenience function to get a logger instance."""
    return PokemonAILogger.get_logger(name)


def configure_logging(debug: bool = False, process_name: str = "main") -> None:
    """Convenience function to configure logging."""
    PokemonAILogger.configure(debug=debug, process_name=process_name)


def is_debug_enabled() -> bool:
    """Convenience function to check if debug logging is enabled."""
    return PokemonAILogger.is_debug_enabled()


# Timeline logging utilities for the camera emoji debug logs
class TimelineLogger:
    """Special logger for timeline events with camera emoji."""
    
    def __init__(self, process_name: str):
        self.process_name = process_name
        self.logger = get_logger(f"{process_name}.timeline")
        
    def log_event(self, event_num: int, timestamp_offset: str, description: str) -> None:
        """Log a timeline event with camera emoji and consistent formatting."""
        message = f"📸 TIMELINE T+{timestamp_offset}: {description}"
        # Use INFO level so these always show when process is running
        self.logger.info(message)
        
    def log_frontend_event(self, description: str) -> None:
        """Log a frontend timeline event."""
        message = f"📸 FRONTEND: {description}"
        # Use INFO level so these always show
        self.logger.info(message)


# Pre-configured timeline loggers for each process
def get_timeline_logger(process_name: str) -> TimelineLogger:
    """Get a timeline logger for a specific process."""
    return TimelineLogger(process_name)
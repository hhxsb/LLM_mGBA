"""
Core app configuration for memory system initialization.
"""

from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    """Core application configuration with memory system initialization"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    
    def ready(self):
        """Initialize memory system when Django starts"""
        # Only initialize once to avoid double-initialization in development
        if hasattr(self, '_memory_initialized'):
            return
        
        self._memory_initialized = True
        
        try:
            # Initialize global memory system
            from .memory_service import initialize_global_memory_system
            initialize_global_memory_system()
            logger.info("🧠 Global memory system initialized at Django startup")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize memory system: {e}")
            # Continue without memory system - application should still work
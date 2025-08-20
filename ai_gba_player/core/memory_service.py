"""
Global memory service for AI GBA Player.
Provides a singleton memory system accessible throughout the application.
"""

import logging
from typing import Optional, Any, Dict

logger = logging.getLogger(__name__)

# Global memory system instance
_global_memory_system = None


def initialize_global_memory_system():
    """Initialize the global memory system at Django startup"""
    global _global_memory_system
    
    if _global_memory_system is not None:
        logger.warning("🔄 Memory system already initialized, skipping...")
        return _global_memory_system
    
    try:
        # Import memory system
        from .graphiti_memory import create_memory_system
        
        # Create memory system instance
        _global_memory_system = create_memory_system()
        
        # Log initialization success with system type
        system_type = type(_global_memory_system).__name__
        logger.info(f"✅ Global memory system initialized: {system_type}")
        
        # Print startup message
        print(f"🧠 Memory System: {system_type} initialized globally")
        
        return _global_memory_system
        
    except ImportError as e:
        logger.error(f"❌ Memory system import failed: {e}")
        print(f"⚠️ Memory system unavailable: {e}")
        return None
        
    except Exception as e:
        logger.error(f"❌ Memory system initialization failed: {e}")
        print(f"⚠️ Memory system initialization error: {e}")
        return None


def get_global_memory_system():
    """Get the global memory system instance"""
    global _global_memory_system
    
    if _global_memory_system is None:
        logger.warning("⚠️ Memory system not initialized, attempting initialization...")
        _global_memory_system = initialize_global_memory_system()
    
    return _global_memory_system


def is_memory_system_available() -> bool:
    """Check if memory system is available"""
    return get_global_memory_system() is not None


def get_memory_context(current_situation: str = "", max_objectives: int = 3) -> Dict[str, Any]:
    """Get memory context from global memory system"""
    memory_system = get_global_memory_system()
    
    if memory_system is None:
        return {
            "current_objectives": [],
            "recent_achievements": [],
            "relevant_strategies": [],
            "discovery_suggestions": ["Memory system unavailable"]
        }
    
    try:
        return memory_system.get_memory_context(current_situation, max_objectives)
    except Exception as e:
        logger.error(f"❌ Error getting memory context: {e}")
        return {
            "current_objectives": [],
            "recent_achievements": [],
            "relevant_strategies": [],
            "discovery_suggestions": ["Memory system error"]
        }


def discover_objective(description: str, location: Optional[str] = None, 
                      category: str = "general", priority: int = 5) -> str:
    """Discover a new objective using global memory system"""
    memory_system = get_global_memory_system()
    
    if memory_system is None:
        logger.warning("⚠️ Cannot discover objective - memory system unavailable")
        return ""
    
    try:
        return memory_system.discover_objective(description, location, category, priority)
    except Exception as e:
        logger.error(f"❌ Error discovering objective: {e}")
        return ""


def complete_objective(objective_id: str, location: Optional[str] = None) -> bool:
    """Complete an objective using global memory system"""
    memory_system = get_global_memory_system()
    
    if memory_system is None:
        logger.warning("⚠️ Cannot complete objective - memory system unavailable")
        return False
    
    try:
        return memory_system.complete_objective(objective_id, location)
    except Exception as e:
        logger.error(f"❌ Error completing objective: {e}")
        return False


def learn_strategy(situation: str, button_sequence: list, success: bool, 
                  context: Optional[Dict[str, Any]] = None) -> str:
    """Learn a strategy using global memory system"""
    memory_system = get_global_memory_system()
    
    if memory_system is None:
        logger.warning("⚠️ Cannot learn strategy - memory system unavailable")
        return ""
    
    try:
        return memory_system.learn_strategy(situation, button_sequence, success, context)
    except Exception as e:
        logger.error(f"❌ Error learning strategy: {e}")
        return ""


def get_memory_stats() -> Dict[str, Any]:
    """Get memory system statistics"""
    memory_system = get_global_memory_system()
    
    if memory_system is None:
        return {
            "status": "unavailable",
            "active_objectives": 0,
            "completed_achievements": 0,
            "learned_strategies": 0
        }
    
    try:
        stats = memory_system.get_stats()
        stats["status"] = "available"
        return stats
    except Exception as e:
        logger.error(f"❌ Error getting memory stats: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
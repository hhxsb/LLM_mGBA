"""
Global memory service for AI GBA Player.
Provides a singleton memory system accessible throughout the application.
"""

import logging
from typing import Optional, Any, Dict

logger = logging.getLogger(__name__)

# Global memory system instance
_global_memory_system = None


def determine_memory_system_type(config):
    """Intelligently determine which memory system to use"""
    try:
        memory_config = config.memory_system_config
    except AttributeError:
        # Fallback if memory_system_config property doesn't exist
        memory_config = {
            'enabled': True,
            'system_type': 'auto',
            'llm_provider': 'inherit',
            'api_keys': {},
            'neo4j': {
                'uri': 'bolt://localhost:7687',
                'username': 'neo4j',
                'password': '',
                'database': 'neo4j'
            }
        }
    
    if not memory_config.get('enabled', True):
        return 'disabled'
    
    system_type = memory_config.get('system_type', 'auto')
    
    if system_type == 'simple':
        return 'simple'
    elif system_type == 'graphiti':
        return 'graphiti' if _is_graphiti_available(memory_config, config) else 'simple'
    elif system_type == 'auto':
        # Auto-detection priority: Graphiti > Simple
        if _is_graphiti_available(memory_config, config):
            return 'graphiti'
        else:
            return 'simple'
    
    return 'simple'  # Default fallback


def _is_graphiti_available(memory_config, main_config=None):
    """Check if Graphiti can be initialized"""
    try:
        # Check dependencies
        import graphiti_core
        from neo4j import GraphDatabase
        
        # Check API key availability
        provider = memory_config.get('llm_provider', 'inherit')
        api_key = None
        
        if provider == 'inherit' and main_config:
            # Use main configuration API key
            try:
                main_provider = main_config.llm_provider
                api_key = main_config.providers.get(main_provider, {}).get('api_key')
            except (AttributeError, KeyError):
                api_key = None
        else:
            # Use memory-specific API key
            api_key = memory_config.get('api_keys', {}).get(provider)
        
        if not api_key:
            return False
        
        # Quick validation of Neo4j configuration
        neo4j_config = memory_config.get('neo4j', {})
        neo4j_uri = neo4j_config.get('uri', '')
        neo4j_username = neo4j_config.get('username', '')
        
        if not neo4j_uri or not neo4j_username:
            return False
        
        return True
        
    except ImportError:
        return False
    except Exception as e:
        logger.debug(f"Graphiti availability check failed: {e}")
        return False


def initialize_global_memory_system():
    """Initialize the global memory system at Django startup with smart detection"""
    global _global_memory_system
    
    if _global_memory_system is not None:
        logger.warning("🔄 Memory system already initialized, skipping...")
        return _global_memory_system
    
    try:
        # Get Django configuration
        from dashboard.models import Configuration
        config = Configuration.get_config()
        
        # Determine which memory system to use
        system_type = determine_memory_system_type(config)
        
        if system_type == 'disabled':
            logger.info("🚫 Memory system disabled by configuration")
            print("🚫 Memory System: Disabled by configuration")
            return None
        
        # Import memory system factory
        from .graphiti_memory import create_memory_system
        
        if system_type == 'graphiti':
            # Create Graphiti memory system with Django configuration
            memory_config = config.memory_system_config
            
            # Get API key
            provider = memory_config.get('llm_provider', 'inherit')
            api_key = None
            
            if provider == 'inherit':
                main_provider = config.llm_provider
                api_key = config.providers.get(main_provider, {}).get('api_key')
            else:
                api_key = memory_config.get('api_keys', {}).get(provider)
            
            # Get Neo4j configuration
            neo4j_config = memory_config.get('neo4j', {})
            
            # Create Graphiti system with configuration
            _global_memory_system = create_memory_system(
                system_type='graphiti',
                api_key=api_key,
                llm_provider=provider if provider != 'inherit' else config.llm_provider,
                neo4j_uri=neo4j_config.get('uri', 'bolt://localhost:7687'),
                neo4j_user=neo4j_config.get('username', 'neo4j'),
                neo4j_password=neo4j_config.get('password', ''),
                graphiti_config=memory_config.get('graphiti_config', {})
            )
        else:
            # Create simple memory system
            _global_memory_system = create_memory_system(system_type='simple')
        
        # Log initialization success with system type
        system_name = type(_global_memory_system).__name__
        logger.info(f"✅ Global memory system initialized: {system_name}")
        
        # Print startup message with enhanced info
        if system_type == 'graphiti':
            print(f"🧠 Memory System: {system_name} initialized globally (Advanced AI Memory)")
        else:
            print(f"🧠 Memory System: {system_name} initialized globally")
        
        return _global_memory_system
        
    except Exception as e:
        logger.error(f"❌ Memory system initialization failed: {e}")
        print(f"⚠️ Memory system initialization error: {e}")
        
        # Fallback to simple memory system
        try:
            from .graphiti_memory import SimpleMemorySystem
            _global_memory_system = SimpleMemorySystem()
            logger.info("🔄 Fell back to SimpleMemorySystem")
            print("🔄 Memory System: Fallback to SimpleMemorySystem")
            return _global_memory_system
        except Exception as fallback_error:
            logger.error(f"❌ Even fallback memory system failed: {fallback_error}")
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
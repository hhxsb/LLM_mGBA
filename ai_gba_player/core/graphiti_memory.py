#!/usr/bin/env python3
"""
Graphiti-based memory system for AI GBA Player.
Provides autonomous objective discovery, achievement tracking, and strategy learning.
"""

import os
import json
import time
import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
from datetime import datetime

try:
    from graphiti_core import Graphiti
    from neo4j import GraphDatabase
    GRAPHITI_AVAILABLE = True
except ImportError:
    GRAPHITI_AVAILABLE = False
    logging.warning("Graphiti not available. Install with: pip install graphiti-core neo4j")


@dataclass
class GameObjective:
    """Represents a discovered game objective"""
    id: str
    description: str
    discovered_at: float
    completed_at: Optional[float] = None
    location_discovered: Optional[str] = None
    priority: int = 5  # 1-10 scale
    category: str = "general"  # "main", "side", "exploration", "collection"
    prerequisites: List[str] = None
    
    def __post_init__(self):
        if self.prerequisites is None:
            self.prerequisites = []


@dataclass
class GameAchievement:
    """Represents a completed achievement"""
    id: str
    title: str
    description: str
    completed_at: float
    location_completed: Optional[str] = None
    prerequisites_met: List[str] = None
    
    def __post_init__(self):
        if self.prerequisites_met is None:
            self.prerequisites_met = []


@dataclass
class GameStrategy:
    """Represents a learned strategy or pattern"""
    id: str
    situation_description: str
    button_sequence: List[str]
    success_rate: float
    times_used: int
    last_used: float
    context: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.context is None:
            self.context = {}


class GraphitiMemorySystem:
    """
    Advanced memory system using Graphiti for autonomous learning.
    Tracks objectives, achievements, and strategies as the AI plays.
    """
    
    def __init__(self, neo4j_uri: str = "bolt://localhost:7687", 
                 neo4j_user: str = "neo4j", neo4j_password: str = "password"):
        self.logger = logging.getLogger(__name__)
        
        if not GRAPHITI_AVAILABLE:
            raise ImportError("Graphiti is not installed. Install with: pip install graphiti-core neo4j")
        
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        
        # Initialize Graphiti client
        try:
            # Check for required environment variables
            import os
            if not os.getenv('OPENAI_API_KEY'):
                self.logger.warning("⚠️ OPENAI_API_KEY not set - Graphiti requires an API key")
                self.graphiti = None
                return
            
            self.graphiti = Graphiti(
                uri=neo4j_uri,
                user=neo4j_user,
                password=neo4j_password
            )
            self.logger.info("✅ Graphiti memory system initialized")
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Graphiti: {e}")
            self.graphiti = None
        
        # In-memory caches for performance
        self.active_objectives: Dict[str, GameObjective] = {}
        self.completed_achievements: Dict[str, GameAchievement] = {}
        self.learned_strategies: Dict[str, GameStrategy] = {}
        
        # Load existing data from Graphiti (skip for now due to async requirements)
        # TODO: Implement proper async knowledge loading
        # self._load_existing_knowledge()
    
    def _load_existing_knowledge(self):
        """Load existing objectives, achievements, and strategies from Graphiti"""
        if not self.graphiti:
            return
        
        try:
            # Query for existing objectives
            objectives_query = """
            MATCH (obj:Objective)
            RETURN obj.id as id, obj.description as description, 
                   obj.discovered_at as discovered_at, obj.completed_at as completed_at,
                   obj.location_discovered as location_discovered, obj.priority as priority,
                   obj.category as category
            """
            
            # Query for achievements
            achievements_query = """
            MATCH (ach:Achievement)
            RETURN ach.id as id, ach.title as title, ach.description as description,
                   ach.completed_at as completed_at, ach.location_completed as location_completed
            """
            
            # Query for strategies
            strategies_query = """
            MATCH (strat:Strategy)
            RETURN strat.id as id, strat.situation_description as situation_description,
                   strat.button_sequence as button_sequence, strat.success_rate as success_rate,
                   strat.times_used as times_used, strat.last_used as last_used
            """
            
            # Load objectives
            results = self.graphiti.search(objectives_query)
            for record in results.get('records', []):
                obj = GameObjective(
                    id=record['id'],
                    description=record['description'],
                    discovered_at=record['discovered_at'],
                    completed_at=record.get('completed_at'),
                    location_discovered=record.get('location_discovered'),
                    priority=record.get('priority', 5),
                    category=record.get('category', 'general')
                )
                if not obj.completed_at:  # Only keep active objectives
                    self.active_objectives[obj.id] = obj
            
            self.logger.info(f"📚 Loaded {len(self.active_objectives)} active objectives")
            
        except Exception as e:
            self.logger.error(f"❌ Error loading existing knowledge: {e}")
    
    def discover_objective(self, description: str, location: Optional[str] = None, 
                          category: str = "general", priority: int = 5) -> str:
        """
        Discover a new objective based on AI observation.
        Returns the objective ID.
        """
        if not self.graphiti:
            return ""
        
        objective_id = f"obj_{int(time.time())}_{hash(description) % 10000}"
        current_time = time.time()
        
        objective = GameObjective(
            id=objective_id,
            description=description,
            discovered_at=current_time,
            location_discovered=location,
            category=category,
            priority=priority
        )
        
        try:
            # Add to Graphiti knowledge graph
            episode_data = {
                "entity_type": "Objective",
                "entity_id": objective_id,
                "description": description,
                "discovered_at": current_time,
                "location_discovered": location or "unknown",
                "category": category,
                "priority": priority,
                "status": "active"
            }
            
            self.graphiti.add_episode(
                episode_id=f"discovery_{objective_id}",
                entities=[episode_data],
                content=f"Discovered new objective: {description}"
            )
            
            # Add to local cache
            self.active_objectives[objective_id] = objective
            
            self.logger.info(f"🎯 Discovered objective: {description}")
            return objective_id
            
        except Exception as e:
            self.logger.error(f"❌ Error discovering objective: {e}")
            return ""
    
    def complete_objective(self, objective_id: str, location: Optional[str] = None) -> bool:
        """
        Mark an objective as completed.
        Returns True if successful.
        """
        if not self.graphiti or objective_id not in self.active_objectives:
            return False
        
        objective = self.active_objectives[objective_id]
        current_time = time.time()
        
        try:
            # Update in Graphiti
            episode_data = {
                "entity_type": "ObjectiveCompletion",
                "entity_id": f"{objective_id}_completion",
                "objective_id": objective_id,
                "completed_at": current_time,
                "location_completed": location or "unknown"
            }
            
            self.graphiti.add_episode(
                episode_id=f"completion_{objective_id}",
                entities=[episode_data],
                content=f"Completed objective: {objective.description}"
            )
            
            # Move to achievements
            achievement = GameAchievement(
                id=objective_id,
                title=objective.description,
                description=f"Completed: {objective.description}",
                completed_at=current_time,
                location_completed=location
            )
            
            self.completed_achievements[objective_id] = achievement
            del self.active_objectives[objective_id]
            
            self.logger.info(f"✅ Completed objective: {objective.description}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error completing objective: {e}")
            return False
    
    def learn_strategy(self, situation: str, button_sequence: List[str], 
                      success: bool, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Learn a new strategy or update an existing one.
        Returns the strategy ID.
        """
        if not self.graphiti:
            return ""
        
        strategy_id = f"strat_{hash(situation) % 10000}"
        current_time = time.time()
        
        if strategy_id in self.learned_strategies:
            # Update existing strategy
            strategy = self.learned_strategies[strategy_id]
            strategy.times_used += 1
            strategy.last_used = current_time
            
            # Update success rate
            if success:
                strategy.success_rate = (strategy.success_rate * (strategy.times_used - 1) + 1.0) / strategy.times_used
            else:
                strategy.success_rate = (strategy.success_rate * (strategy.times_used - 1)) / strategy.times_used
        else:
            # Create new strategy
            strategy = GameStrategy(
                id=strategy_id,
                situation_description=situation,
                button_sequence=button_sequence,
                success_rate=1.0 if success else 0.0,
                times_used=1,
                last_used=current_time,
                context=context or {}
            )
            self.learned_strategies[strategy_id] = strategy
        
        try:
            # Update in Graphiti
            episode_data = {
                "entity_type": "Strategy",
                "entity_id": strategy_id,
                "situation_description": situation,
                "button_sequence": json.dumps(button_sequence),
                "success_rate": strategy.success_rate,
                "times_used": strategy.times_used,
                "last_used": current_time,
                "success": success
            }
            
            self.graphiti.add_episode(
                episode_id=f"strategy_{strategy_id}_{int(current_time)}",
                entities=[episode_data],
                content=f"{'Successful' if success else 'Failed'} strategy for: {situation}"
            )
            
            self.logger.info(f"🧠 {'Updated' if strategy.times_used > 1 else 'Learned'} strategy: {situation}")
            return strategy_id
            
        except Exception as e:
            self.logger.error(f"❌ Error learning strategy: {e}")
            return ""
    
    def get_current_objectives(self, category: Optional[str] = None, max_count: int = 5) -> List[GameObjective]:
        """Get current active objectives, optionally filtered by category"""
        objectives = list(self.active_objectives.values())
        
        if category:
            objectives = [obj for obj in objectives if obj.category == category]
        
        # Sort by priority (higher first) and discovery time
        objectives.sort(key=lambda x: (-x.priority, x.discovered_at))
        
        return objectives[:max_count]
    
    def get_relevant_strategies(self, situation: str, min_success_rate: float = 0.5) -> List[GameStrategy]:
        """Get strategies relevant to the current situation"""
        relevant_strategies = []
        
        for strategy in self.learned_strategies.values():
            # Simple keyword matching for now - could be enhanced with embeddings
            if (any(word in strategy.situation_description.lower() for word in situation.lower().split()) and
                strategy.success_rate >= min_success_rate):
                relevant_strategies.append(strategy)
        
        # Sort by success rate and recency
        relevant_strategies.sort(key=lambda x: (-x.success_rate, -x.last_used))
        
        return relevant_strategies[:3]  # Top 3 strategies
    
    def get_memory_context(self, current_situation: str = "", max_objectives: int = 3) -> Dict[str, Any]:
        """
        Get memory context for the LLM including objectives, achievements, and strategies.
        """
        context = {
            "current_objectives": [],
            "recent_achievements": [],
            "relevant_strategies": [],
            "discovery_suggestions": []
        }
        
        # Current objectives
        objectives = self.get_current_objectives(max_count=max_objectives)
        context["current_objectives"] = [
            {
                "description": obj.description,
                "priority": obj.priority,
                "category": obj.category,
                "location_discovered": obj.location_discovered
            }
            for obj in objectives
        ]
        
        # Recent achievements (last 5)
        recent_achievements = sorted(
            self.completed_achievements.values(),
            key=lambda x: x.completed_at,
            reverse=True
        )[:5]
        
        context["recent_achievements"] = [
            {
                "title": ach.title,
                "completed_at": datetime.fromtimestamp(ach.completed_at).strftime("%Y-%m-%d %H:%M"),
                "location": ach.location_completed
            }
            for ach in recent_achievements
        ]
        
        # Relevant strategies for current situation
        if current_situation:
            strategies = self.get_relevant_strategies(current_situation)
            context["relevant_strategies"] = [
                {
                    "situation": strat.situation_description,
                    "buttons": strat.button_sequence,
                    "success_rate": f"{strat.success_rate:.1%}",
                    "times_used": strat.times_used
                }
                for strat in strategies
            ]
        
        # Suggestions for new discoveries
        context["discovery_suggestions"] = [
            "Look for NPCs to talk to - they often provide objectives",
            "Check for items or interactable objects",
            "Notice location names and landmarks for navigation",
            "Observe battle outcomes and Pokemon interactions"
        ]
        
        return context
    
    def query_knowledge(self, query: str) -> Dict[str, Any]:
        """
        Query the knowledge graph using natural language.
        Returns relevant information.
        """
        if not self.graphiti:
            return {"error": "Graphiti not available"}
        
        try:
            results = self.graphiti.search(query)
            return {
                "query": query,
                "results": results,
                "timestamp": time.time()
            }
        except Exception as e:
            self.logger.error(f"❌ Error querying knowledge: {e}")
            return {"error": str(e)}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory system statistics"""
        return {
            "active_objectives": len(self.active_objectives),
            "completed_achievements": len(self.completed_achievements),
            "learned_strategies": len(self.learned_strategies),
            "total_strategy_uses": sum(s.times_used for s in self.learned_strategies.values()),
            "avg_strategy_success": sum(s.success_rate for s in self.learned_strategies.values()) / len(self.learned_strategies) if self.learned_strategies else 0
        }


# Fallback memory system for when Graphiti is not available
class SimpleMemorySystem:
    """
    Simple in-memory fallback when Graphiti is not available.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.warning("⚠️ Using simple memory system - Graphiti not available")
        
        self.objectives: Dict[str, Dict] = {}
        self.achievements: List[Dict] = []
        self.strategies: Dict[str, Dict] = {}
    
    def discover_objective(self, description: str, location: Optional[str] = None, 
                          category: str = "general", priority: int = 5) -> str:
        objective_id = f"obj_{int(time.time())}"
        self.objectives[objective_id] = {
            "description": description,
            "discovered_at": time.time(),
            "location": location,
            "category": category,
            "priority": priority
        }
        self.logger.info(f"🎯 Simple: Discovered objective: {description}")
        return objective_id
    
    def complete_objective(self, objective_id: str, location: Optional[str] = None) -> bool:
        if objective_id in self.objectives:
            obj = self.objectives.pop(objective_id)
            self.achievements.append({
                "title": obj["description"],
                "completed_at": time.time(),
                "location": location
            })
            self.logger.info(f"✅ Simple: Completed objective: {obj['description']}")
            return True
        return False
    
    def learn_strategy(self, situation: str, button_sequence: List[str], 
                      success: bool, context: Optional[Dict[str, Any]] = None) -> str:
        strategy_id = f"strat_{hash(situation) % 10000}"
        if strategy_id not in self.strategies:
            self.strategies[strategy_id] = {
                "situation": situation,
                "buttons": button_sequence,
                "success_count": 0,
                "total_count": 0
            }
        
        self.strategies[strategy_id]["total_count"] += 1
        if success:
            self.strategies[strategy_id]["success_count"] += 1
        
        return strategy_id
    
    def get_memory_context(self, current_situation: str = "", max_objectives: int = 3) -> Dict[str, Any]:
        return {
            "current_objectives": [
                {"description": obj["description"], "priority": obj["priority"]}
                for obj in list(self.objectives.values())[:max_objectives]
            ],
            "recent_achievements": self.achievements[-3:],
            "relevant_strategies": [],
            "discovery_suggestions": ["Simple memory system active - limited features"]
        }
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "active_objectives": len(self.objectives),
            "completed_achievements": len(self.achievements),
            "learned_strategies": len(self.strategies)
        }


def create_memory_system(neo4j_uri: str = "bolt://localhost:7687", 
                        neo4j_user: str = "neo4j", 
                        neo4j_password: str = "password"):
    """
    Factory function to create the appropriate memory system.
    Returns GraphitiMemorySystem if available, otherwise SimpleMemorySystem.
    """
    if GRAPHITI_AVAILABLE:
        try:
            memory_system = GraphitiMemorySystem(neo4j_uri, neo4j_user, neo4j_password)
            # Check if GraphitiMemorySystem successfully initialized
            if memory_system.graphiti is None:
                logging.info("🔄 Graphiti not fully initialized, falling back to simple memory system")
                return SimpleMemorySystem()
            return memory_system
        except Exception as e:
            logging.error(f"❌ Failed to create Graphiti memory system: {e}")
            logging.info("🔄 Falling back to simple memory system")
            return SimpleMemorySystem()
    else:
        return SimpleMemorySystem()
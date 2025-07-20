#!/usr/bin/env python3
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import os

@dataclass
class Location:
    """Represents a game location with connections and features"""
    map_id: int
    name: str
    coordinates: Tuple[int, int]
    connections: Dict[str, int] = None  # direction -> map_id
    npcs: List[Dict[str, Any]] = None
    items: List[str] = None
    obstacles: List[Dict[str, Any]] = None
    exits: List[Dict[str, Any]] = None
    visited_count: int = 0
    last_visited: float = 0
    
    def __post_init__(self):
        if self.connections is None:
            self.connections = {}
        if self.npcs is None:
            self.npcs = []
        if self.items is None:
            self.items = []
        if self.obstacles is None:
            self.obstacles = []
        if self.exits is None:
            self.exits = []

@dataclass
class Goal:
    """Represents a game goal with status and attempts"""
    id: str
    description: str
    type: str  # "main", "sub", "exploration", "collection"
    status: str  # "active", "completed", "failed", "blocked"
    priority: int  # 1-10, higher is more important
    location_id: Optional[int] = None
    prerequisites: List[str] = None
    attempts: List[Dict[str, Any]] = None
    created_time: float = 0
    completed_time: Optional[float] = None
    
    def __post_init__(self):
        if self.prerequisites is None:
            self.prerequisites = []
        if self.attempts is None:
            self.attempts = []
        if self.created_time == 0:
            self.created_time = time.time()

@dataclass
class FailurePattern:
    """Tracks patterns of failed actions for learning"""
    pattern_id: str
    situation: str  # Description of the situation
    failed_actions: List[str]  # Actions that didn't work
    successful_alternative: Optional[str] = None
    occurrence_count: int = 1
    last_seen: float = 0
    
    def __post_init__(self):
        if self.last_seen == 0:
            self.last_seen = time.time()

@dataclass
class NPCInteraction:
    """Tracks NPC interactions and dialogue"""
    npc_id: str
    location_id: int
    position: Tuple[int, int]
    name: Optional[str] = None
    dialogue_history: List[Dict[str, Any]] = None
    items_given: List[str] = None
    quests_received: List[str] = None
    interaction_count: int = 0
    last_interaction: float = 0
    
    def __post_init__(self):
        if self.dialogue_history is None:
            self.dialogue_history = []
        if self.items_given is None:
            self.items_given = []
        if self.quests_received is None:
            self.quests_received = []

class KnowledgeGraph:
    """Advanced knowledge system for Pokemon AI"""
    
    def __init__(self, knowledge_file: str = "data/knowledge_graph.json"):
        self.knowledge_file = knowledge_file
        self.locations: Dict[int, Location] = {}
        self.goals: Dict[str, Goal] = {}
        self.failure_patterns: Dict[str, FailurePattern] = {}
        self.npc_interactions: Dict[str, NPCInteraction] = {}
        self.action_history: deque = deque(maxlen=100)  # Recent actions for pattern detection
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(knowledge_file), exist_ok=True)
        
        # Load existing knowledge
        self.load_knowledge()
        
        # Initialize with basic Pokemon Red goals if empty
        if not self.goals:
            self._initialize_basic_goals()
    
    def load_knowledge(self):
        """Load knowledge from JSON file"""
        try:
            if os.path.exists(self.knowledge_file):
                with open(self.knowledge_file, 'r') as f:
                    data = json.load(f)
                
                # Reconstruct objects from JSON
                self.locations = {
                    int(k): Location(**v) for k, v in data.get('locations', {}).items()
                }
                self.goals = {
                    k: Goal(**v) for k, v in data.get('goals', {}).items()
                }
                self.failure_patterns = {
                    k: FailurePattern(**v) for k, v in data.get('failure_patterns', {}).items()
                }
                self.npc_interactions = {
                    k: NPCInteraction(**v) for k, v in data.get('npc_interactions', {}).items()
                }
                self.action_history = deque(data.get('action_history', []), maxlen=100)
                
                print(f"✅ Loaded knowledge graph with {len(self.locations)} locations, {len(self.goals)} goals")
        except Exception as e:
            print(f"⚠️ Error loading knowledge: {e}")
            print("Starting with fresh knowledge base")
    
    def save_knowledge(self):
        """Save knowledge to JSON file"""
        try:
            data = {
                'locations': {k: asdict(v) for k, v in self.locations.items()},
                'goals': {k: asdict(v) for k, v in self.goals.items()},
                'failure_patterns': {k: asdict(v) for k, v in self.failure_patterns.items()},
                'npc_interactions': {k: asdict(v) for k, v in self.npc_interactions.items()},
                'action_history': list(self.action_history)
            }
            
            with open(self.knowledge_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"⚠️ Error saving knowledge: {e}")
    
    def update_location(self, map_id: int, name: str, x: int, y: int, direction: str):
        """Update location information"""
        if map_id not in self.locations:
            self.locations[map_id] = Location(
                map_id=map_id,
                name=name,
                coordinates=(x, y)
            )
        
        location = self.locations[map_id]
        location.visited_count += 1
        location.last_visited = time.time()
        
        # Update coordinates if they've changed (moving within the map)
        location.coordinates = (x, y)
        
        self.save_knowledge()
    
    def detect_goals_from_text(self, text: str) -> List[Goal]:
        """Automatically detect goals from game text/dialogue"""
        new_goals = []
        
        # Goal detection patterns
        goal_patterns = [
            # Quest/task patterns
            (r"deliver this to|bring this to|take this to", "delivery", 5),
            (r"find|locate|search for", "find", 4),
            (r"beat|defeat|fight", "battle", 6),
            (r"collect|gather|catch", "collection", 3),
            (r"go to|visit|travel to", "travel", 2),
            (r"talk to|speak with|see", "interaction", 2),
        ]
        
        import re
        text_lower = text.lower()
        
        for pattern, goal_type, priority in goal_patterns:
            if re.search(pattern, text_lower):
                goal_id = f"auto_{goal_type}_{int(time.time())}"
                goal = Goal(
                    id=goal_id,
                    description=f"Auto-detected: {text[:100]}...",
                    type=goal_type,
                    status="active",
                    priority=priority
                )
                new_goals.append(goal)
                self.goals[goal_id] = goal
        
        return new_goals
    
    def record_failure_pattern(self, situation: str, failed_actions: List[str], current_location: int):
        """Record a pattern of failed actions"""
        pattern_id = f"fail_{hash(situation + str(failed_actions)) % 10000}"
        
        if pattern_id in self.failure_patterns:
            self.failure_patterns[pattern_id].occurrence_count += 1
            self.failure_patterns[pattern_id].last_seen = time.time()
        else:
            self.failure_patterns[pattern_id] = FailurePattern(
                pattern_id=pattern_id,
                situation=situation,
                failed_actions=failed_actions
            )
        
        self.save_knowledge()
    
    def get_alternative_actions(self, situation: str) -> List[str]:
        """Get alternative actions based on learned failure patterns"""
        alternatives = []
        
        for pattern in self.failure_patterns.values():
            if situation.lower() in pattern.situation.lower():
                if pattern.successful_alternative:
                    alternatives.append(pattern.successful_alternative)
        
        return alternatives
    
    def record_action(self, action: str, result: str, location: int, success: bool):
        """Record an action and its result"""
        action_record = {
            "action": action,
            "result": result,
            "location": location,
            "success": success,
            "timestamp": time.time()
        }
        
        self.action_history.append(action_record)
        
        # Detect repeated failures
        recent_failures = [a for a in list(self.action_history)[-10:] if not a["success"]]
        if len(recent_failures) >= 3:
            failed_actions = [a["action"] for a in recent_failures]
            situation = f"location_{location}_repeated_failures"
            self.record_failure_pattern(situation, failed_actions, location)
    
    def get_active_goals(self) -> List[Goal]:
        """Get currently active goals, sorted by priority"""
        active_goals = [g for g in self.goals.values() if g.status == "active"]
        return sorted(active_goals, key=lambda x: x.priority, reverse=True)
    
    def complete_goal(self, goal_id: str):
        """Mark a goal as completed"""
        if goal_id in self.goals:
            self.goals[goal_id].status = "completed"
            self.goals[goal_id].completed_time = time.time()
            self.save_knowledge()
    
    def get_location_context(self, map_id: int) -> str:
        """Get contextual information about a location"""
        if map_id not in self.locations:
            return "Unknown location - first visit"
        
        location = self.locations[map_id]
        context = f"Location: {location.name}\n"
        context += f"Visited {location.visited_count} times\n"
        
        if location.npcs:
            context += f"NPCs here: {len(location.npcs)}\n"
        
        if location.items:
            context += f"Items found: {', '.join(location.items)}\n"
        
        # Check for recent failures at this location
        recent_failures = [a for a in self.action_history if a["location"] == map_id and not a["success"]]
        if recent_failures:
            context += f"⚠️ Recent failures here: {len(recent_failures)}\n"
        
        return context
    
    def get_navigation_advice(self, current_location: int, target_location: Optional[int] = None) -> str:
        """Get navigation advice based on learned patterns"""
        advice = []
        
        # Check for known failure patterns at current location
        location_failures = [p for p in self.failure_patterns.values() 
                           if f"location_{current_location}" in p.situation]
        
        for failure in location_failures:
            if failure.successful_alternative:
                advice.append(f"💡 Try: {failure.successful_alternative} (learned from {failure.occurrence_count} failures)")
        
        return "\n".join(advice) if advice else "No specific navigation advice available"
    
    def _initialize_basic_goals(self):
        """Initialize with basic Pokemon Red goals"""
        basic_goals = [
            Goal("name_character", "Enter player name as GEMINI", "setup", "active", 10),
            Goal("get_starter", "Get first Pokemon from Professor Oak", "main", "active", 9),
            Goal("exit_pallet_town", "Leave Pallet Town and start journey", "main", "active", 8),
            Goal("reach_viridian_city", "Reach Viridian City", "main", "active", 7),
            Goal("get_pokedex", "Obtain the Pokedex", "main", "active", 6),
        ]
        
        for goal in basic_goals:
            self.goals[goal.id] = goal
        
        self.save_knowledge()
    
    def generate_context_summary(self) -> str:
        """Generate a summary of current knowledge for the AI"""
        summary = "## AI Knowledge Summary\n\n"
        
        # Active goals
        active_goals = self.get_active_goals()
        if active_goals:
            summary += "### Current Goals (by priority):\n"
            for goal in active_goals[:5]:  # Top 5 goals
                summary += f"- {goal.description} (priority: {goal.priority})\n"
            summary += "\n"
        
        # Recent locations
        recent_locations = sorted(self.locations.values(), 
                                key=lambda x: x.last_visited, reverse=True)[:3]
        if recent_locations:
            summary += "### Recent Locations:\n"
            for loc in recent_locations:
                summary += f"- {loc.name} (visited {loc.visited_count} times)\n"
            summary += "\n"
        
        # Failure patterns
        recent_failures = sorted(self.failure_patterns.values(), 
                               key=lambda x: x.last_seen, reverse=True)[:3]
        if recent_failures:
            summary += "### Recent Learning:\n"
            for failure in recent_failures:
                summary += f"- Learned to avoid: {', '.join(failure.failed_actions)} in {failure.situation}\n"
            summary += "\n"
        
        return summary
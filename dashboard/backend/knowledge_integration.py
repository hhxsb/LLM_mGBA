"""
Knowledge system integration for the dashboard
Provides real-time access to knowledge data for the UI
"""
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import time
import logging

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from games.pokemon_red.knowledge_system import PokemonRedKnowledgeSystem
from core.base_knowledge_system import Goal, ActionRecord, DialogueRecord

logger = logging.getLogger(__name__)

class DashboardKnowledgeInterface:
    """Interface between knowledge system and dashboard"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.knowledge_file = config.get('knowledge_file', 'data/knowledge_graph.json')
        self.knowledge_system = None
        self._last_update = 0
        self._cached_data = {}
        
        # Try to initialize knowledge system
        self._initialize_knowledge_system()
    
    def _initialize_knowledge_system(self):
        """Initialize the knowledge system"""
        try:
            self.knowledge_system = PokemonRedKnowledgeSystem(self.knowledge_file)
            logger.info("✅ Knowledge system initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize knowledge system: {e}")
            self.knowledge_system = None
    
    def is_available(self) -> bool:
        """Check if knowledge system is available"""
        return self.knowledge_system is not None
    
    def get_current_tasks(self) -> List[Dict[str, Any]]:
        """Get current active tasks from knowledge system"""
        if not self.is_available():
            return self._get_mock_tasks()
        
        try:
            active_goals = self.knowledge_system.get_active_goals()
            tasks = []
            
            for goal in active_goals:
                # Map Goal to dashboard task format
                task = {
                    'id': goal.id,
                    'title': goal.description,
                    'description': goal.description,
                    'priority': self._map_priority(goal.priority),
                    'status': self._map_status(goal.status),
                    'category': goal.type or 'general',
                    'location_id': getattr(goal, 'location_id', None),
                    'prerequisites': getattr(goal, 'prerequisites', []) or [],
                    'created_at': getattr(goal, 'created_at', time.time()),
                    'updated_at': getattr(goal, 'updated_at', time.time())
                }
                tasks.append(task)
            
            # Sort by priority and creation time
            tasks.sort(key=lambda x: (-self._priority_value(x['priority']), x['created_at']))
            return tasks
            
        except Exception as e:
            logger.error(f"❌ Error getting current tasks: {e}")
            return self._get_mock_tasks()
    
    def get_knowledge_summary(self) -> Dict[str, Any]:
        """Get summary of knowledge system state"""
        if not self.is_available():
            return self._get_mock_summary()
        
        try:
            active_goals = self.knowledge_system.get_active_goals()
            all_goals = list(self.knowledge_system.goals.values())
            
            # Calculate progress stats
            completed_goals = [g for g in all_goals if g.status == 'completed']
            in_progress_goals = [g for g in all_goals if g.status == 'active']
            pending_goals = [g for g in all_goals if g.status == 'pending']
            
            # Get recent activity
            recent_actions = self.knowledge_system.action_history[-10:] if self.knowledge_system.action_history else []
            recent_dialogues = self.knowledge_system.get_recent_dialogues(5)
            
            # Character state
            character_state = self.knowledge_system.character_state
            
            return {
                'character': {
                    'name': character_state.name,
                    'current_objective': character_state.current_objective,
                    'game_phase': character_state.game_phase,
                    'tutorial_progress': len(character_state.tutorial_progress)
                },
                'tasks': {
                    'total': len(all_goals),
                    'completed': len(completed_goals),
                    'active': len(in_progress_goals),
                    'pending': len(pending_goals)
                },
                'recent_activity': {
                    'actions': len(recent_actions),
                    'dialogues': len(recent_dialogues),
                    'last_action': recent_actions[-1].action if recent_actions else None,
                    'last_dialogue': recent_dialogues[0].npc_name if recent_dialogues else None
                },
                'locations': {
                    'discovered': len(self.knowledge_system.locations),
                    'current': getattr(self.knowledge_system.conversation_state, 'location_id', None)
                },
                'updated_at': time.time()
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting knowledge summary: {e}")
            return self._get_mock_summary()
    
    def get_location_info(self, location_id: int = None) -> Dict[str, Any]:
        """Get information about a specific location"""
        if not self.is_available():
            return {'name': 'Unknown Location', 'description': 'Knowledge system not available'}
        
        try:
            if location_id and location_id in self.knowledge_system.locations:
                location = self.knowledge_system.locations[location_id]
                return {
                    'id': location.id,
                    'name': location.name,
                    'description': location.description,
                    'exits': location.exits,
                    'npcs': location.npcs,
                    'items': location.items,
                    'visited_count': location.visited_count
                }
            else:
                # Get current location context
                context = self.knowledge_system.get_location_context(location_id or 0)
                return {
                    'id': location_id,
                    'name': 'Current Location',
                    'description': context,
                    'context': True
                }
                
        except Exception as e:
            logger.error(f"❌ Error getting location info: {e}")
            return {'name': 'Error', 'description': str(e)}
    
    def get_tutorial_progress(self) -> Dict[str, Any]:
        """Get tutorial progress information"""
        if not self.is_available():
            return self._get_mock_tutorial_progress()
        
        try:
            character_state = self.knowledge_system.character_state
            tutorial_guidance = self.knowledge_system.get_current_tutorial_guidance()
            progress_summary = self.knowledge_system.get_tutorial_progress_summary()
            next_steps = self.knowledge_system.get_next_tutorial_steps_preview(3)
            
            return {
                'completed_steps': character_state.tutorial_progress,
                'current_phase': character_state.game_phase,
                'guidance': tutorial_guidance,
                'progress_summary': progress_summary,
                'next_steps': next_steps,
                'total_completed': len(character_state.tutorial_progress)
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting tutorial progress: {e}")
            return self._get_mock_tutorial_progress()
    
    def get_npc_interactions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent NPC interactions"""
        if not self.is_available():
            return []
        
        try:
            recent_dialogues = self.knowledge_system.get_recent_dialogues(limit)
            interactions = []
            
            for dialogue in recent_dialogues:
                interaction = {
                    'npc_name': dialogue.npc_name,
                    'npc_role': dialogue.npc_role,
                    'dialogue_text': dialogue.dialogue_text[:100] + '...' if len(dialogue.dialogue_text) > 100 else dialogue.dialogue_text,
                    'player_response': dialogue.player_response,
                    'outcome': dialogue.outcome,
                    'timestamp': dialogue.timestamp,
                    'location_id': dialogue.location_id,
                    'important_info': dialogue.important_info
                }
                interactions.append(interaction)
            
            return interactions
            
        except Exception as e:
            logger.error(f"❌ Error getting NPC interactions: {e}")
            return []
    
    def add_task(self, title: str, description: str, priority: str = 'medium', category: str = 'general') -> bool:
        """Add a new task to the knowledge system"""
        if not self.is_available():
            return False
        
        try:
            # Create new goal
            goal_id = f"dashboard_task_{int(time.time())}"
            goal = Goal(
                id=goal_id,
                description=title,
                type=category,
                status='active',
                priority=self._priority_value(priority),
                created_at=time.time(),
                updated_at=time.time()
            )
            
            self.knowledge_system.goals[goal_id] = goal
            self.knowledge_system.save_knowledge()
            
            logger.info(f"✅ Added new task: {title}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error adding task: {e}")
            return False
    
    def update_task_status(self, task_id: str, new_status: str) -> bool:
        """Update the status of a task"""
        if not self.is_available():
            return False
        
        try:
            if task_id in self.knowledge_system.goals:
                goal = self.knowledge_system.goals[task_id]
                goal.status = self._map_status_reverse(new_status)
                goal.updated_at = time.time()
                
                self.knowledge_system.save_knowledge()
                logger.info(f"✅ Updated task {task_id} status to {new_status}")
                return True
            else:
                logger.warning(f"⚠️ Task not found: {task_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error updating task status: {e}")
            return False
    
    # Helper methods
    def _map_priority(self, priority_num: int) -> str:
        """Map numeric priority to string"""
        if priority_num >= 8:
            return 'high'
        elif priority_num >= 5:
            return 'medium'
        else:
            return 'low'
    
    def _priority_value(self, priority_str: str) -> int:
        """Map string priority to numeric value"""
        priority_map = {'high': 10, 'medium': 5, 'low': 1}
        return priority_map.get(priority_str, 5)
    
    def _map_status(self, status: str) -> str:
        """Map knowledge system status to dashboard status"""
        status_map = {
            'active': 'in_progress',
            'completed': 'completed',
            'pending': 'pending',
            'failed': 'pending'
        }
        return status_map.get(status, 'pending')
    
    def _map_status_reverse(self, dashboard_status: str) -> str:
        """Map dashboard status to knowledge system status"""
        status_map = {
            'in_progress': 'active',
            'completed': 'completed',
            'pending': 'pending'
        }
        return status_map.get(dashboard_status, 'pending')
    
    # Mock data methods (fallbacks when knowledge system is unavailable)
    def _get_mock_tasks(self) -> List[Dict[str, Any]]:
        """Provide mock tasks when knowledge system is unavailable"""
        return [
            {
                'id': 'mock_1',
                'title': 'Get starter Pokemon',
                'description': 'Visit Professor Oak to receive your first Pokemon',
                'priority': 'high',
                'status': 'in_progress',
                'category': 'main_quest',
                'created_at': time.time() - 3600,
                'updated_at': time.time() - 1800
            },
            {
                'id': 'mock_2',
                'title': 'Explore Pallet Town',
                'description': 'Familiarize yourself with the starting town',
                'priority': 'medium',
                'status': 'completed',
                'category': 'exploration',
                'created_at': time.time() - 7200,
                'updated_at': time.time() - 3600
            },
            {
                'id': 'mock_3',
                'title': 'Learn about Pokemon types',
                'description': 'Understand type advantages and weaknesses',
                'priority': 'medium',
                'status': 'pending',
                'category': 'learning',
                'created_at': time.time() - 1800,
                'updated_at': time.time() - 1800
            }
        ]
    
    def _get_mock_summary(self) -> Dict[str, Any]:
        """Provide mock summary when knowledge system is unavailable"""
        return {
            'character': {
                'name': 'TRAINER',
                'current_objective': 'Learn Pokemon basics',
                'game_phase': 'tutorial',
                'tutorial_progress': 2
            },
            'tasks': {
                'total': 5,
                'completed': 1,
                'active': 2,
                'pending': 2
            },
            'recent_activity': {
                'actions': 10,
                'dialogues': 3,
                'last_action': 'move_north',
                'last_dialogue': 'Professor Oak'
            },
            'locations': {
                'discovered': 2,
                'current': 1
            },
            'updated_at': time.time(),
            'mock_data': True
        }
    
    def _get_mock_tutorial_progress(self) -> Dict[str, Any]:
        """Provide mock tutorial progress when knowledge system is unavailable"""
        return {
            'completed_steps': ['game_start', 'met_professor_oak'],
            'current_phase': 'tutorial',
            'guidance': 'Visit Professor Oak to get your starter Pokemon',
            'progress_summary': 'Started your Pokemon journey in Pallet Town',
            'next_steps': 'Get starter Pokemon, learn basic controls, explore town',
            'total_completed': 2,
            'mock_data': True
        }
#!/usr/bin/env python3
"""
Pokemon Red specific knowledge system implementation.
"""

from typing import Dict, List, Any
import sys
import os
import time

# Add parent directories to path to import core modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from core.base_knowledge_system import BaseKnowledgeSystem, Goal, ActionRecord, LocationInfo
from core.base_game_engine import GameState


class PokemonRedKnowledgeSystem(BaseKnowledgeSystem):
    """Knowledge system specifically for Pokemon Red."""
    
    def __init__(self, knowledge_file: str):
        super().__init__(knowledge_file, "pokemon_red")
        
        # Pokemon-specific data structures
        self.pokemon_data = self.game_specific_data.get('pokemon_data', {})
        self.gym_data = self.game_specific_data.get('gym_data', {})
        self.trainer_data = self.game_specific_data.get('trainer_data', {})
        self.item_data = self.game_specific_data.get('item_data', {})
        
        # Initialize Pokemon-specific goals if not loaded
        self._initialize_pokemon_goals()
    
    def _initialize_pokemon_goals(self):
        """Initialize default Pokemon Red goals."""
        default_goals = [
            Goal(
                id="get_starter_pokemon",
                description="Get starter Pokémon from Professor Oak",
                type="main",
                status="active" if not self.goals else "active",
                priority=10,
                location_id=40  # Oak's Lab
            ),
            Goal(
                id="defeat_rival_first_battle", 
                description="Defeat rival in first battle",
                type="main",
                status="active",
                priority=9,
                prerequisites=["get_starter_pokemon"]
            ),
            Goal(
                id="deliver_parcel_to_oak",
                description="Deliver Oak's Parcel from Viridian City Mart",
                type="main", 
                status="active",
                priority=8
            ),
            Goal(
                id="defeat_brock",
                description="Defeat Brock at Pewter City Gym",
                type="main",
                status="active",
                priority=7,
                location_id=48  # Pewter City Gym
            ),
            Goal(
                id="defeat_misty",
                description="Defeat Misty at Cerulean City Gym", 
                type="main",
                status="active",
                priority=7
            ),
            Goal(
                id="defeat_lt_surge",
                description="Defeat Lt. Surge at Vermillion City Gym",
                type="main",
                status="active", 
                priority=7
            ),
            Goal(
                id="defeat_elite_four",
                description="Defeat the Elite Four and become Champion",
                type="main",
                status="active",
                priority=10
            ),
            Goal(
                id="complete_pokedex",
                description="Catch all 150 Pokémon",
                type="collection",
                status="active",
                priority=5
            )
        ]
        
        # Add goals that don't already exist
        for goal in default_goals:
            if goal.id not in self.goals:
                self.goals[goal.id] = goal
        
        # Save if we added new goals
        if default_goals:
            self.save_knowledge()
    
    def generate_context_summary(self) -> str:
        """Generate Pokemon Red specific context summary."""
        active_goals = self.get_active_goals()
        context = "\n## Pokemon Red Knowledge Summary\n"
        
        # Current objectives
        if active_goals:
            context += "### Current Objectives:\n"
            sorted_goals = sorted(active_goals, key=lambda x: x.priority, reverse=True)
            for goal in sorted_goals[:3]:  # Top 3 priorities
                context += f"- {goal.description} (Priority: {goal.priority})\n"
        
        # Pokemon team info (placeholder - would need memory reading)
        context += "\n### Pokémon Team:\n"
        if self.pokemon_data.get('team'):
            for pokemon in self.pokemon_data['team']:
                context += f"- {pokemon.get('name', 'Unknown')} (Level {pokemon.get('level', '?')})\n"
        else:
            context += "- No Pokémon data available (requires memory reading)\n"
        
        # Gym progress
        context += "\n### Gym Progress:\n"
        gym_badges = self.gym_data.get('badges', [])
        if gym_badges:
            for badge in gym_badges:
                context += f"- {badge} Badge: Obtained\n"
        else:
            context += "- No gym badges yet\n"
        
        # Recent discoveries
        recent_locations = sorted(
            self.locations.values(), 
            key=lambda x: getattr(x, 'last_visited', 0), 
            reverse=True
        )[:3]
        
        if recent_locations:
            context += "\n### Recently Visited:\n"
            for loc in recent_locations:
                context += f"- {loc.name}\n"
        
        return context
    
    def get_navigation_advice(self, current_location: int) -> str:
        """Get navigation advice for Pokemon Red."""
        if current_location not in self.locations:
            return ""
        
        location = self.locations[current_location]
        advice = f"\n### Navigation Advice for {location.name}:\n"
        
        # Check for active goals at this location
        location_goals = [g for g in self.get_active_goals() if g.location_id == current_location]
        if location_goals:
            advice += "🎯 **Goals at this location:**\n"
            for goal in location_goals:
                advice += f"- {goal.description}\n"
        
        # Add location-specific advice
        location_advice = self._get_location_specific_advice(current_location)
        if location_advice:
            advice += f"\n📍 **Location Tips:**\n{location_advice}\n"
        
        # Check for nearby important locations
        if hasattr(location, 'connections') and location.connections:
            advice += "\n🗺️ **Connected Areas:**\n"
            for direction, connected_id in location.connections.items():
                connected_name = self.locations.get(connected_id, {}).get('name', f'Map {connected_id}')
                advice += f"- {direction.upper()}: {connected_name}\n"
        
        return advice
    
    def _get_location_specific_advice(self, location_id: int) -> str:
        """Get specific advice for Pokemon Red locations."""
        advice_map = {
            40: "🔬 Professor Oak's Lab - Get your starter Pokémon and Pokédex here",
            37: "🏠 Your house - Talk to your mom for healing and advice", 
            0: "🌳 Pallet Town - Your hometown, start of your journey",
            1: "🏪 Viridian City - Visit the Pokémon Center and Mart, gym is locked initially",
            2: "⛰️ Pewter City - Challenge Brock for your first gym badge",
            3: "💧 Cerulean City - Challenge Misty for the Cascade Badge",
            46: "🌲 Viridian Forest - Catch Bug-type Pokémon, watch for trainers",
            48: "🥊 Pewter Gym - Rock-type specialist, use Water/Grass moves",
            12: "🛤️ Route 1 - First route, wild Pidgey and Rattata",
            13: "🛤️ Route 2 - Leads to Viridian Forest",
        }
        
        return advice_map.get(location_id, "")
    
    def analyze_game_progress(self) -> Dict[str, Any]:
        """Analyze current Pokemon Red game progress."""
        analysis = {
            'completion_percentage': 0,
            'current_phase': 'early_game',
            'recommendations': [],
            'strengths': [],
            'weaknesses': []
        }
        
        # Analyze goals completion
        total_main_goals = len([g for g in self.goals.values() if g.type == "main"])
        completed_main_goals = len([g for g in self.goals.values() if g.type == "main" and g.status == "completed"])
        
        if total_main_goals > 0:
            analysis['completion_percentage'] = (completed_main_goals / total_main_goals) * 100
        
        # Determine game phase
        if completed_main_goals == 0:
            analysis['current_phase'] = 'tutorial'
            analysis['recommendations'].append("Focus on getting your starter Pokémon")
        elif completed_main_goals < 3:
            analysis['current_phase'] = 'early_game'
            analysis['recommendations'].append("Work on first few gym battles")
        elif completed_main_goals < 6:
            analysis['current_phase'] = 'mid_game'
            analysis['recommendations'].append("Continue gym challenge")
        else:
            analysis['current_phase'] = 'late_game'
            analysis['recommendations'].append("Prepare for Elite Four")
        
        # Analyze recent actions for patterns
        recent_failures = [a for a in self.action_history[-10:] if not a.success]
        if len(recent_failures) > 5:
            analysis['weaknesses'].append("High failure rate in recent actions")
            analysis['recommendations'].append("Review recent strategies and try different approaches")
        
        return analysis
    
    def suggest_next_actions(self, game_state: GameState) -> List[str]:
        """Suggest next actions based on Pokemon Red game state."""
        suggestions = []
        
        # Get highest priority active goal
        active_goals = sorted(self.get_active_goals(), key=lambda x: x.priority, reverse=True)
        
        if active_goals:
            top_goal = active_goals[0]
            
            # Goal-specific suggestions
            if top_goal.id == "get_starter_pokemon":
                if game_state.map_id == 40:  # Oak's Lab
                    suggestions.append("Talk to Professor Oak to get your starter Pokémon")
                else:
                    suggestions.append("Go to Professor Oak's Lab to get your starter Pokémon")
            
            elif top_goal.id == "defeat_brock":
                if game_state.map_id == 48:  # Pewter Gym
                    suggestions.append("Challenge Brock - use Water or Grass type moves")
                else:
                    suggestions.append("Head to Pewter City Gym to challenge Brock")
            
            elif "defeat" in top_goal.id and "gym" in top_goal.description.lower():
                suggestions.append(f"Work towards: {top_goal.description}")
        
        # Location-specific suggestions
        if game_state.map_id in [41, 49]:  # Pokémon Centers
            suggestions.append("Heal your Pokémon at the Pokémon Center")
        elif game_state.map_id in [42, 50]:  # Poké Marts
            suggestions.append("Buy items like Poké Balls and Potions")
        
        # General exploration if no specific goals
        if not suggestions:
            suggestions.append("Explore the area and look for NPCs to talk to")
            suggestions.append("Check for items on the ground")
            suggestions.append("Look for new areas to explore")
        
        return suggestions
    
    def record_pokemon_encounter(self, pokemon_name: str, location_id: int, caught: bool = False):
        """Record a Pokémon encounter."""
        if 'pokemon_encounters' not in self.game_specific_data:
            self.game_specific_data['pokemon_encounters'] = {}
        
        encounters = self.game_specific_data['pokemon_encounters']
        if pokemon_name not in encounters:
            encounters[pokemon_name] = {
                'first_seen': time.time(),
                'locations': [],
                'encounter_count': 0,
                'caught': False
            }
        
        encounter_data = encounters[pokemon_name]
        encounter_data['encounter_count'] += 1
        
        if location_id not in encounter_data['locations']:
            encounter_data['locations'].append(location_id)
        
        if caught:
            encounter_data['caught'] = True
        
        self.save_knowledge()
    
    def record_gym_victory(self, gym_leader: str, badge_name: str):
        """Record a gym victory."""
        if 'badges' not in self.gym_data:
            self.gym_data['badges'] = []
        
        if badge_name not in self.gym_data['badges']:
            self.gym_data['badges'].append(badge_name)
            
            # Mark related goal as completed
            gym_goal_id = f"defeat_{gym_leader.lower().replace(' ', '_')}"
            if gym_goal_id in self.goals:
                self.complete_goal(gym_goal_id)
        
        self.game_specific_data['gym_data'] = self.gym_data
        self.save_knowledge()
    
    def get_pokemon_team_summary(self) -> str:
        """Get a summary of the current Pokémon team."""
        if not self.pokemon_data.get('team'):
            return "No Pokémon team data available (requires memory reading integration)"
        
        summary = "Current Pokémon Team:\n"
        for i, pokemon in enumerate(self.pokemon_data['team'], 1):
            name = pokemon.get('name', 'Unknown')
            level = pokemon.get('level', '?')
            hp = pokemon.get('hp', '?')
            summary += f"{i}. {name} (Level {level}, HP: {hp})\n"
        
        return summary
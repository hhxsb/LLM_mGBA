"""
Context Builder Module for LLM Client

Handles prompt context creation, spatial awareness, and game state formatting.
Provides clean separation of context building logic from API calls.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List


class ContextBuilder:
    """
    Builds contextualized prompts for LLM analysis.
    
    Handles:
    - Game state context formatting
    - Spatial awareness and navigation hints
    - Notepad content management
    - Memory system integration
    - Prompt template loading and processing
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize context builder with configuration.
        
        Args:
            config: Configuration dictionary containing paths and settings
        """
        self.config = config
        self.notepad_path = Path(config.get('notepad_path', 'data/notepad.txt'))
        self.prompt_template_path = Path(config.get('prompt_template_path', 'data/prompt_template.txt'))
        self.prompt_template = ""
        self.prompt_template_mtime = 0
        self._load_prompt_template()
    
    def _load_prompt_template(self):
        """Load prompt template with hot-reload capability"""
        try:
            if self.prompt_template_path.exists():
                current_mtime = self.prompt_template_path.stat().st_mtime
                if current_mtime != self.prompt_template_mtime:
                    with open(self.prompt_template_path, 'r', encoding='utf-8') as f:
                        self.prompt_template = f.read()
                    self.prompt_template_mtime = current_mtime
                    print(f"📝 Loaded prompt template from {self.prompt_template_path}")
            else:
                print(f"⚠️ Prompt template not found: {self.prompt_template_path}")
                self.prompt_template = self._get_default_template()
        except Exception as e:
            print(f"❌ Error loading prompt template: {e}")
            self.prompt_template = self._get_default_template()
    
    def _get_default_template(self) -> str:
        """Get default prompt template if file is not available"""
        return """You are an AI playing Pokemon Red. Analyze the screenshot and make the best decision.

{spatial_context}

{recent_actions}

{direction_guidance}

{notepad_content}

Choose the best action to progress in the game."""
    
    def create_game_context(self, game_state: Dict[str, Any], recent_actions_text: str = "", 
                           before_after_analysis: str = "") -> str:
        """
        Create comprehensive game context for LLM analysis.
        
        Args:
            game_state: Current game state (position, direction, map, etc.)
            recent_actions_text: Description of recent player actions
            before_after_analysis: Analysis of changes between screenshots
            
        Returns:
            str: Formatted prompt context for LLM
        """
        # Reload template if changed (hot-reload)
        self._load_prompt_template()
        
        # Extract game state information
        current_map = game_state.get('current_map', 'Unknown')
        x = game_state.get('x', 0)
        y = game_state.get('y', 0) 
        direction = game_state.get('direction', 'UNKNOWN')
        map_id = game_state.get('map_id', -1)
        
        # Build context components
        spatial_context = self.get_spatial_context(current_map, x, y, direction, map_id)
        direction_guidance = self._get_direction_guidance_text(direction, x, y, map_id)
        notepad_content = self._read_notepad()
        
        # Get memory context if available
        memory_context = self._get_memory_context(current_map, x, y, direction, map_id)
        
        # Format the template
        try:
            context = self.prompt_template.format(
                spatial_context=spatial_context,
                recent_actions=recent_actions_text if recent_actions_text else "No recent actions recorded.",
                direction_guidance=direction_guidance,
                notepad_content=notepad_content,
                memory_context=memory_context,
                before_after_analysis=before_after_analysis if before_after_analysis else ""
            )
        except KeyError as e:
            print(f"⚠️ Missing template variable: {e}")
            # Fallback to basic template
            context = self._create_basic_context(game_state, recent_actions_text, before_after_analysis)
        
        return context
    
    def create_comparison_context(self, game_state: Dict[str, Any], recent_actions_text: str = "") -> str:
        """
        Create context for screenshot comparison analysis.
        
        Args:
            game_state: Current game state
            recent_actions_text: Description of recent actions
            
        Returns:
            str: Formatted comparison context for LLM
        """
        # Load template
        self._load_prompt_template()
        
        # Build basic context
        current_map = game_state.get('current_map', 'Unknown')
        x = game_state.get('x', 0)
        y = game_state.get('y', 0)
        direction = game_state.get('direction', 'UNKNOWN')
        map_id = game_state.get('map_id', -1)
        
        spatial_context = self.get_spatial_context(current_map, x, y, direction, map_id)
        notepad_content = self._read_notepad()
        
        comparison_prompt = f"""You are an AI playing Pokemon Red. You will see two screenshots: BEFORE and AFTER.

TASK: Compare the two images and determine what action to take next.

{spatial_context}

{recent_actions_text if recent_actions_text else "No recent actions recorded."}

{notepad_content}

Analyze the differences between BEFORE and AFTER images, then choose your next action."""
        
        return comparison_prompt
    
    def get_spatial_context(self, current_map: str, x: int, y: int, direction: str, map_id: int) -> str:
        """
        Create spatial context describing current location and surroundings.
        
        Args:
            current_map: Name of current map/location
            x, y: Current coordinates
            direction: Current facing direction
            map_id: Numeric map identifier
            
        Returns:
            str: Formatted spatial context
        """
        context_parts = []
        
        # Basic location info
        context_parts.append(f"📍 **Current Location**: {current_map}")
        context_parts.append(f"🧭 **Position**: ({x}, {y}) facing {direction}")
        
        # Map-specific context
        map_context = self._get_map_specific_context(map_id, current_map, x, y)
        if map_context:
            context_parts.append(f"🗺️ **Area Info**: {map_context}")
        
        # Movement suggestions
        movement_hints = self._generate_movement_suggestions(direction, x, y, map_id)
        if movement_hints:
            context_parts.append(f"💡 **Navigation Hints**:")
            context_parts.append(movement_hints)
        
        return "\n".join(context_parts)
    
    def _get_map_specific_context(self, map_id: int, map_name: str, x: int, y: int) -> str:
        """Get context specific to the current map"""
        if map_id == 0:  # Pallet Town
            if y < 8:
                return "Northern area - Professor Oak's lab should be nearby"
            elif y > 12:
                return "Southern residential area - houses and starting point"
            elif x < 8:
                return "Western side - Red's house area"  
            elif x > 12:
                return "Eastern side - Blue's house area"
        
        elif map_id == 37:  # Red's House 1F
            return "Inside Red's house - look for stairs to go up or door to exit"
        
        elif map_id == 40:  # Oak's Lab
            return "Professor Oak's lab - look for Oak or Pokeball on table"
        
        elif map_id == 1:  # Route 1
            return "Route 1 - path between Pallet Town and Viridian City"
        
        elif map_id == 2:  # Viridian City
            return "Viridian City - Pokemon Center, Gym, and shop available"
        
        return f"Map {map_id} ({map_name})"
    
    def _generate_movement_suggestions(self, direction: str, x: int, y: int, map_id: int) -> str:
        """Generate movement suggestions based on current state"""
        suggestions = []
        
        # Direction-based suggestions
        if direction in ['UP', 'DOWN', 'LEFT', 'RIGHT']:
            suggestions.append(f"- You're facing {direction} - you can move forward or turn")
            if direction in ['LEFT', 'RIGHT']:
                suggestions.append("- To interact with objects above/below, turn UP or DOWN first")
            else:
                suggestions.append("- To interact with objects left/right, turn LEFT or RIGHT first") 
        else:
            suggestions.append("- Direction unknown - try pressing a directional button to orient yourself")
        
        # Position-specific suggestions for known maps
        if map_id == 0:  # Pallet Town
            if y < 8:
                suggestions.append("- You're in the northern area - Oak's lab should be nearby")
            elif y > 12:
                suggestions.append("- You're in the southern area - near the houses")
            
            if x < 8:
                suggestions.append("- Western side of town - Red's house area")
            elif x > 12:
                suggestions.append("- Eastern side of town - Blue's house area")
        
        elif map_id == 37:  # Red's House 1F
            suggestions.append("- Look for stairs (usually dark colored) to go upstairs")
            suggestions.append("- Look for the door (usually at bottom) to exit outside")
        
        elif map_id == 40:  # Oak's Lab
            suggestions.append("- Look for Professor Oak to talk to him")
            suggestions.append("- Examine the Pokeball on the table if you haven't chosen a starter")
        
        # General movement optimization
        suggestions.append("- If you see a clear path, move towards your objective")
        suggestions.append("- If blocked, try moving around obstacles or look for alternative routes")
        
        return "\n".join(suggestions)
    
    def _get_direction_guidance_text(self, direction: str, x: int, y: int, map_id: int) -> str:
        """Get direction-specific guidance text"""
        if direction == 'UP':
            return "You're facing UP. You can move forward (UP) or interact with objects above you (A button)."
        elif direction == 'DOWN': 
            return "You're facing DOWN. You can move forward (DOWN) or interact with objects below you (A button)."
        elif direction == 'LEFT':
            return "You're facing LEFT. You can move forward (LEFT) or interact with objects to your left (A button)."
        elif direction == 'RIGHT':
            return "You're facing RIGHT. You can move forward (RIGHT) or interact with objects to your right (A button)."
        else:
            return "Direction is unknown. Try pressing a directional button to orient yourself."
    
    def _read_notepad(self) -> str:
        """Read the current notepad content for memory"""
        try:
            if self.notepad_path.exists():
                with open(self.notepad_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        return f"📝 **Game Progress Notes**:\n{content}"
                    else:
                        return "📝 **Game Progress Notes**: No progress recorded yet."
            else:
                return "📝 **Game Progress Notes**: Game just started. No progress recorded yet."
        except Exception as e:
            print(f"❌ Error reading notepad: {e}")
            return "📝 **Game Progress Notes**: Error reading progress file."
    
    def update_notepad(self, new_content: str) -> None:
        """Update the notepad with new progress information"""
        try:
            current_content = self._read_notepad() 
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            updated_content = f"{current_content}\n\n## Update {timestamp}\n{new_content}"
            
            # Ensure directory exists
            self.notepad_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.notepad_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            print("📝 Notepad updated")
        except Exception as e:
            print(f"❌ Error updating notepad: {e}")
    
    def _get_memory_context(self, current_map: str, x: int, y: int, direction: str, map_id: int) -> str:
        """Get memory context from global memory system if available"""
        try:
            from core.memory_service import MEMORY_SERVICE_AVAILABLE, get_memory_context, get_memory_stats
            
            if not MEMORY_SERVICE_AVAILABLE:
                return ""
            
            # Get current situation for context
            current_situation = f"at {current_map} ({x}, {y}) facing {direction}"
            memory_data = get_memory_context(current_situation)
            
            # Format memory context for LLM
            memory_lines = []
            
            # Current objectives
            if memory_data.get("current_objectives"):
                memory_lines.append("## 🎯 Current Objectives:")
                for obj in memory_data["current_objectives"]:
                    priority_emoji = "🔥" if obj["priority"] >= 8 else "⭐" if obj["priority"] >= 6 else "📋"
                    memory_lines.append(f"  {priority_emoji} {obj['description']} (Priority: {obj['priority']})")
                    if obj.get("location_discovered"):
                        memory_lines.append(f"     📍 Discovered at: {obj['location_discovered']}")
                memory_lines.append("")
            
            # Recent achievements
            if memory_data.get("recent_achievements"):
                memory_lines.append("## 🏆 Recent Achievements:")
                for ach in memory_data["recent_achievements"]:
                    memory_lines.append(f"  ✅ {ach['title']} (Completed: {ach['completed_at']})")
                    if ach.get("location"):
                        memory_lines.append(f"     📍 Completed at: {ach['location']}")
                memory_lines.append("")
            
            # Relevant strategies
            if memory_data.get("relevant_strategies"):
                memory_lines.append("## 🧠 Learned Strategies:")
                for strat in memory_data["relevant_strategies"]:
                    buttons_str = " → ".join(strat["buttons"])
                    memory_lines.append(f"  💡 {strat['situation']}: [{buttons_str}]")
                    memory_lines.append(f"     📊 Success rate: {strat['success_rate']} (Used {strat['times_used']} times)")
                memory_lines.append("")
            
            return "\n".join(memory_lines) if memory_lines else ""
            
        except Exception as e:
            print(f"⚠️ Error getting memory context: {e}")
            return "## 🧠 Memory System: Temporarily unavailable"
    
    def _create_basic_context(self, game_state: Dict[str, Any], recent_actions: str, 
                             before_after: str) -> str:
        """Create basic context when template formatting fails"""
        current_map = game_state.get('current_map', 'Unknown')
        x = game_state.get('x', 0)
        y = game_state.get('y', 0)
        direction = game_state.get('direction', 'UNKNOWN')
        
        return f"""You are an AI playing Pokemon Red.

Current Location: {current_map}
Position: ({x}, {y}) facing {direction}

{recent_actions if recent_actions else "No recent actions."}

{before_after if before_after else ""}

Analyze the screenshot and choose the best action to progress in the game."""
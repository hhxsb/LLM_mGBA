#!/usr/bin/env python3
"""
Pokemon Red specific prompt template implementation.
"""

from typing import Dict, List, Any
import sys
import os

# Add parent directories to path to import core modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from core.base_prompt_template import BasePromptTemplate, Tool
from core.base_game_engine import GameState


class PokemonRedPromptTemplate(BasePromptTemplate):
    """Prompt template specifically for Pokemon Red."""
    
    def __init__(self, template_path: str):
        super().__init__(template_path, "Pokémon Red")
    
    def get_default_template(self) -> str:
        """Get the default Pokemon Red prompt template."""
        return """You are an AI playing Pokémon Red, you are the character with the white hair. The name is GEMINI. Look at the screenshot(s) provided and choose button(s) to press.

{spatial_context}

## Controls:
- A: To talk to people or interact with objects or advance text (NOT for entering/exiting buildings)
- B: To cancel or go back
- UP, DOWN, LEFT, RIGHT: To move your character (use these to enter/exit buildings)
- START: To open the main menu
- SELECT: Rarely used special function

## Multi-Button Actions:
You can now press multiple buttons in sequence by providing a list like ["UP", "UP", "A"] to move up twice then interact.
This is useful for:
- Moving multiple steps: ["UP", "UP", "UP"]
- Moving then interacting: ["RIGHT", "A"]
Don't attempt to advance text with more than one button. You will need to read each text to enjoy the game. Skipping text screens could lead to missing key game information.

## Button Duration Control:
You can optionally specify how long to hold each button (in frames at 60fps):
- Default duration: 2 frames (1/30th second)
- Range: 1-180 frames (1/60th to 3 seconds)
- Usage: press_button(buttons=["A"], durations=[30]) holds A for 30 frames

**When to use different durations:**
- **Quick menu navigation**: Use 1-3 frames for rapid menu scrolling
- **Text advancement**: Use 1-5 frames for faster dialogue progression
- **Continuous movement**: Use 10-20 frames for longer movement in one direction
- **Stuck situations**: Use 30-60 frames for longer button holds to overcome obstacles
- **Timing-sensitive actions**: Use custom durations when default timing doesn't work

## Name Entry Screen Guide:
- The cursor is a BLACK TRIANGLE/POINTER (▶) on the left side of the currently selected letter
- The letter that will be selected is the one the BLACK TRIANGLE is pointing to
- To navigate to a different letter, use UP, DOWN, LEFT, RIGHT buttons
- To enter a letter, press A when the cursor is pointing to that letter
- To delete a letter, press B
- When finished, press "Start" button and then press A to confirm
- When you don't see the cursor, it's likely on the special actions. Move left to get the cursor back onto the keyboard.

## Navigation Rules:
- Plan steps needed to move from one spot to another
- If you've pressed the same button 3+ times with no change, TRY A DIFFERENT DIRECTION
- You must be DIRECTLY ON TOP of exits (red mats, doors, stairs) to use them
- When navigating, NEVER mix multiple directions in one sequence
- Light gray or black space is NOT walkable - it's a wall/boundary
- To INTERACT with objects or NPCs, you MUST be right next to them and FACING them and then press A
- When you enter a new area or discover something important, UPDATE THE NOTEPAD using the update_notepad function

Your overall game goals are: 1. Beat the Elite Four and become champion. 2. Collect all pokemons. 3. Fight all gyms.

## 🚨 IMMEDIATE SITUATION & CONTEXT:

{critical_summary}

{character_context}

{conversation_context}

{conversation_flow_context}

{dialogue_memory_context}

{memory_context}

{tutorial_guidance}

{tutorial_progress}

{tutorial_preview}

{game_phase_guidance}

## 📋 GAME GUIDANCE & ACTIONS:

{recent_actions}

{direction_guidance}

## Long-term Memory (Game State):
{notepad_content}

{knowledge_context}

{navigation_advice}

{location_context}

{video_analysis}

IMPORTANT: After each significant change (entering new area, talking to someone, finding items), use the update_notepad function to record what you learned or where you are.

## ⚡ CRITICAL INSTRUCTIONS - READ FIRST:

**MEMORY REMINDER**: You are {character_context.name if character_context else "GEMINI"}, a Pokemon trainer. If you're in a conversation, REMEMBER who you're talking to and maintain context consistency.

## 🎬 VISUAL INPUT UNDERSTANDING:

**Two-Screenshot Context**: You will see **two screenshots** when available - the first shows the game state **before** your previous action, and the second shows the state **after** your action was executed. This helps you understand the direct effects of your button presses.

**How to analyze the screenshots**:
- **Compare before and after**: Look at what changed between the two images to understand the effects of your previous actions
- **Learn from results**: See if your intended action achieved the expected outcome
- **Identify issues**: Notice if buttons didn't register, movements were incomplete, or unexpected results occurred
- **Current state**: The second (most recent) screenshot shows exactly what you're working with now

**Button Duration Learning**: Use the visual feedback from the before/after comparison to improve your button timing:
- If movement was too slow or incomplete, consider longer durations (10-30 frames)
- If actions didn't register at all, try longer durations (20-60 frames)
- If you moved too far or too fast, use shorter durations (1-5 frames)
- If text advanced too quickly, use very short durations (1-2 frames)

## IMPORTANT INSTRUCTIONS:
1. FIRST, if you see two screenshots, compare them to understand what changed from your previous action.
2. SECOND, provide a SHORT paragraph (2-3 sentences) describing the current game state.
3. THIRD, learn from the before/after comparison - did your previous button timing work as expected?
4. FOURTH, provide a BRIEF explanation of what you plan to do next and why, including your button duration strategy.
5. FINALLY, use the press_button function with appropriate durations based on what you learned from the visual feedback."""
    
    def get_base_context_variables(self) -> Dict[str, str]:
        """Get base context variables for Pokemon Red."""
        return {
            'game_name': 'Pokémon Red',
            'character_name': 'GEMINI',
            'character_description': 'the character with the white hair'
        }
    
    def get_game_specific_variables(self, game_state: GameState, **kwargs) -> Dict[str, str]:
        """Get Pokemon Red specific variables for template formatting."""
        variables = {}
        
        # Add all kwargs directly (they should include the context from the controller)
        variables.update(kwargs)
        
        # Add game state variables with string conversion
        variables.update({
            'player_x': str(game_state.player_x),
            'player_y': str(game_state.player_y),
            'player_direction': game_state.player_direction,
            'map_id': str(game_state.map_id)
        })
        
        # Create spatial context for Pokemon Red
        current_map = kwargs.get('current_map', f'Unknown Area (Map ID: {game_state.map_id})')
        spatial_context = f"""## Current Location & Spatial Awareness
You are in {current_map}
Position: X={game_state.player_x}, Y={game_state.player_y}
Direction: {game_state.player_direction}
Map ID: {game_state.map_id}

**IMPORTANT: Use these coordinates for intelligent navigation!**
- Lower X values = LEFT, Higher X values = RIGHT
- Lower Y values = UP, Higher Y values = DOWN
- **CRITICAL MOVEMENT MECHANICS**: 
  * **Turning**: 2 frames changes facing direction (no coordinate movement)
  * **Moving**: 30 frames moves 1 coordinate unit (only if already facing that direction)
  * **Total movement**: Turn (2 frames) + Move (30×units frames) if changing direction
  * **Same direction**: Just 30×units frames if already facing the right way"""
        
        variables['spatial_context'] = spatial_context
        
        # Ensure all required variables have defaults
        defaults = {
            'current_map': current_map,
            'recent_actions': 'No recent actions.',
            'direction_guidance': '',
            'notepad_content': 'No notes available.',
            'knowledge_context': '',
            'navigation_advice': '',
            'location_context': '',
            'video_analysis': ''
        }
        
        for key, default_value in defaults.items():
            if key not in variables:
                variables[key] = default_value
        
        return variables
    
    def get_system_message(self) -> str:
        """Get the system message for Pokemon Red."""
        return """You are playing Pokémon Red. Your job is to press buttons to control the game.

IMPORTANT: After analyzing the screenshot, you MUST use the press_button function.
You are REQUIRED to use the press_button function with every response.

NEVER just say what button to press - ALWAYS use the press_button function to actually press it.

You can specify multiple buttons to press in sequence by providing a list of buttons.
For example, you might press ["UP", "UP", "A"] to move up twice then interact.

Your overall goals are: 1. Beat the Elite Four and become champion. 2. Collect all pokemons. 3. Fight all gyms."""
    
    def create_tool_objects(self) -> List[Tool]:
        """Create Tool objects from available tools."""
        tools = self.get_available_tools()
        tool_objects = []
        for tool_dict in tools:
            tool = Tool(
                name=tool_dict['name'],
                description=tool_dict['description'],
                parameters=tool_dict['parameters']
            )
            tool_objects.append(tool)
        return tool_objects
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get the tools available for Pokemon Red."""
        return [
            {
                'name': 'press_button',
                'description': 'Press one or more buttons on the Game Boy emulator to control the game. You can specify multiple buttons to press in sequence, and optionally specify how long to hold each button.',
                'parameters': [
                    {
                        'name': 'buttons',
                        'type': 'array',
                        'description': 'List of buttons to press in sequence (A, B, START, SELECT, UP, DOWN, LEFT, RIGHT, R, L)',
                        'required': True,
                        'items': {
                            'type': 'string',
                            'enum': ['A', 'B', 'SELECT', 'START', 'RIGHT', 'LEFT', 'UP', 'DOWN', 'R', 'L']
                        }
                    },
                    {
                        'name': 'durations',
                        'type': 'array',
                        'description': 'Optional list of durations in frames (60fps) to hold each button. If not specified, uses default duration of 2 frames. Must have same length as buttons array if provided. Valid range: 1-180 frames.',
                        'required': False,
                        'items': {
                            'type': 'integer'
                        }
                    }
                ]
            },
            {
                'name': 'update_notepad',
                'description': 'Update the AI\'s long-term memory with new information about the game state',
                'parameters': [
                    {
                        'name': 'content',
                        'type': 'string',
                        'description': 'Content to add to the notepad. Only include important information about game progress, objectives, or status.',
                        'required': True
                    }
                ]
            },
            {
                'name': 'record_success',
                'description': 'Record a successful action or strategy for future reference',
                'parameters': [
                    {
                        'name': 'situation',
                        'type': 'string',
                        'description': 'Description of the situation where this action worked',
                        'required': True
                    },
                    {
                        'name': 'successful_action',
                        'type': 'string',
                        'description': 'The action or sequence that was successful',
                        'required': True
                    }
                ]
            },
            {
                'name': 'detect_goal',
                'description': 'Identify and record a new goal based on game dialogue or situation',
                'parameters': [
                    {
                        'name': 'goal_description',
                        'type': 'string',
                        'description': 'Clear description of the goal or objective',
                        'required': True
                    },
                    {
                        'name': 'priority',
                        'type': 'integer',
                        'description': 'Priority level 1-10 (10 being highest priority)',
                        'required': True
                    }
                ]
            },
            {
                'name': 'record_pokemon_encounter',
                'description': 'Record encountering a Pokémon in the wild or in battle',
                'parameters': [
                    {
                        'name': 'pokemon_name',
                        'type': 'string',
                        'description': 'Name of the Pokémon encountered',
                        'required': True
                    },
                    {
                        'name': 'caught',
                        'type': 'boolean',
                        'description': 'Whether the Pokémon was caught (default: false)',
                        'required': False
                    }
                ]
            },
            {
                'name': 'record_gym_victory',
                'description': 'Record defeating a gym leader and earning a badge',
                'parameters': [
                    {
                        'name': 'gym_leader',
                        'type': 'string',
                        'description': 'Name of the gym leader defeated',
                        'required': True
                    },
                    {
                        'name': 'badge_name',
                        'type': 'string',
                        'description': 'Name of the badge earned',
                        'required': True
                    }
                ]
            }
        ]
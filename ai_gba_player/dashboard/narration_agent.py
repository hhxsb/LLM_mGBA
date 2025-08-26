#!/usr/bin/env python3
"""
NarrationAgent - Handles narrative generation for AI gameplay entertainment.
Uses configured LLM provider for dynamic, entertaining commentary and narration.
"""

import time
import os
from typing import Dict, Any, Optional, List
from .models import Configuration
from .llm_client import LLMClient


class NarrationResponse:
    """Structured response from NarrationAgent narration generation"""
    
    def __init__(self, success: bool = True, narration: str = "", 
                 dialogue_reading: str = "", scene_description: str = "",
                 excitement_level: str = "neutral", error: str = ""):
        self.success = success
        self.narration = narration
        self.dialogue_reading = dialogue_reading  # TTS-friendly dialogue reading
        self.scene_description = scene_description
        self.excitement_level = excitement_level  # low, neutral, high, epic
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "success": self.success,
            "narration": self.narration,
            "dialogue_reading": self.dialogue_reading,
            "scene_description": self.scene_description,
            "excitement_level": self.excitement_level,
            "error": self.error
        }


class NarrationAgent:
    """AI agent responsible for generating entertaining narration for streaming audiences"""
    
    def __init__(self):
        # LLM client for narration generation (supports multiple providers)
        self.llm_client = None
        
        # Session-based context memory
        self.session_context = {
            "recent_events": [],  # Last 5-10 significant events
            "character_state": {},  # Player status, location context
            "ongoing_narrative": "",  # Current story thread
            "dialogue_history": []  # Recent NPC interactions
        }
        
        # Narration configuration
        self.max_context_events = 10
        self.narration_styles = {
            "exploration": "curious and observant",
            "battle": "intense and exciting", 
            "dialogue": "character-focused and engaging",
            "discovery": "wonder and excitement",
            "stuck": "encouraging and strategic"
        }
        
        print("🎤 NarrationAgent initialized - ready for entertaining commentary")
    
    def initialize_llm(self, config: Dict[str, Any]):
        """Initialize LLM client with same config as PlayerAgent"""
        try:
            if not self.llm_client:
                self.llm_client = LLMClient(config)
                print(f"🤖 NarrationAgent: LLM client initialized with {config.get('llm_provider', 'google')} provider")
            return True
            
        except Exception as e:
            print(f"❌ NarrationAgent: Failed to initialize LLM client: {e}")
            return False
    
    def generate_narration(self, player_response: Dict[str, Any], 
                          game_context: Dict[str, Any]) -> NarrationResponse:
        """Generate entertaining narration based on player actions and game state"""
        
        if not self.llm_client:
            config = self._load_config()
            if not config or not self.initialize_llm(config):
                return NarrationResponse(
                    success=False,
                    error="LLM client not initialized",
                    narration="Unable to generate narration - AI not available"
                )
        
        try:
            # Update session context with new information
            self._update_session_context(player_response, game_context)
            
            # Determine narration style based on game context
            style = self._determine_narration_style(game_context, player_response)
            
            # Build narration prompt
            prompt = self._build_narration_prompt(player_response, game_context, style)
            
            # Call LLM for narration
            print(f"🎤 Generating narration with {self.llm_client.provider} provider...")
            
            response = self._call_llm_for_narration(prompt)
            
            if not response or not response.get('success'):
                return NarrationResponse(
                    success=False,
                    error=response.get('error', 'Unknown error') if response else 'No response',
                    narration="The adventure continues in silence..."
                )
            
            # Parse the structured narration response
            return self._parse_narration_response(response.get('text', ''), style)
            
        except Exception as e:
            print(f"❌ NarrationAgent error: {e}")
            return NarrationResponse(
                success=False,
                error=str(e),
                narration=f"An unexpected turn in the adventure... {self._get_fallback_narration(game_context)}"
            )
    
    def _update_session_context(self, player_response: Dict[str, Any], game_context: Dict[str, Any]):
        """Update session-based context memory with new information"""
        
        # Extract key information
        current_situation = player_response.get("current_situation", "")
        detected_dialogue = player_response.get("detected_dialogue", "")
        actions_taken = player_response.get("actions", [])
        game_analysis = player_response.get("game_analysis", "")
        
        # Update character state
        position = game_context.get("position", {})
        self.session_context["character_state"] = {
            "location": f"({position.get('x', 0)}, {position.get('y', 0)})",
            "direction": game_context.get("direction", "UNKNOWN"),
            "map_id": game_context.get("map_id", 0),
            "situation": current_situation
        }
        
        # Add significant events
        if actions_taken or detected_dialogue or "stuck" in current_situation.lower():
            event = {
                "timestamp": time.time(),
                "actions": actions_taken,
                "dialogue": detected_dialogue,
                "situation": current_situation,
                "analysis": game_analysis[:100] + "..." if len(game_analysis) > 100 else game_analysis
            }
            
            self.session_context["recent_events"].append(event)
            
            # Keep only recent events
            if len(self.session_context["recent_events"]) > self.max_context_events:
                self.session_context["recent_events"] = self.session_context["recent_events"][-self.max_context_events:]
        
        # Track dialogue history
        if detected_dialogue:
            self.session_context["dialogue_history"].append({
                "timestamp": time.time(),
                "dialogue": detected_dialogue
            })
            
            # Keep only recent dialogues
            if len(self.session_context["dialogue_history"]) > 5:
                self.session_context["dialogue_history"] = self.session_context["dialogue_history"][-5:]
    
    def _determine_narration_style(self, game_context: Dict[str, Any], 
                                  player_response: Dict[str, Any]) -> str:
        """Determine the appropriate narration style based on context"""
        
        current_situation = player_response.get("current_situation", "").lower()
        detected_dialogue = player_response.get("detected_dialogue", "")
        actions = player_response.get("actions", [])
        
        # Priority-based style determination
        if detected_dialogue:
            return "dialogue"
        elif "battle" in current_situation or "fight" in current_situation:
            return "battle"
        elif "stuck" in current_situation or len(set(actions)) == 1 and len(actions) > 3:
            return "stuck"
        elif "found" in current_situation or "discovered" in current_situation:
            return "discovery"
        else:
            return "exploration"
    
    def _call_llm_for_narration(self, prompt: str) -> Dict[str, Any]:
        """Call the LLM with narration-specific prompt"""
        try:
            # Use LLMClient's text-only generation method
            response = self._call_text_llm(prompt)
            return {
                'success': True,
                'text': response,
                'error': None
            }
        except Exception as e:
            print(f"❌ NarrationAgent LLM call failed: {e}")
            return {
                'success': False,
                'text': '',
                'error': str(e)
            }
    
    def _call_text_llm(self, prompt: str) -> str:
        """Call LLM provider with text-only prompt"""
        if self.llm_client.provider == 'google':
            import google.generativeai as genai
            model = genai.GenerativeModel('gemini-2.0-flash-exp')
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.8,  # Creative but not too random
                    max_output_tokens=300,  # Keep narration concise
                    top_p=0.9
                )
            )
            return response.text if response and response.text else ""
        
        elif self.llm_client.provider == 'openai':
            response = self.llm_client.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Use mini for cost-effective narration
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=300
            )
            return response.choices[0].message.content if response.choices else ""
        
        else:
            # Fallback for unsupported providers
            raise Exception(f"Narration not supported for provider: {self.llm_client.provider}")
    
    def _build_narration_prompt(self, player_response: Dict[str, Any], 
                               game_context: Dict[str, Any], style: str) -> str:
        """Build the narration generation prompt for LLM"""
        
        # Get recent context
        recent_events = self.session_context["recent_events"][-3:]  # Last 3 events
        character_state = self.session_context["character_state"]
        
        # Build context summary
        context_summary = f"Player at {character_state.get('location', 'unknown location')}, facing {character_state.get('direction', 'unknown direction')}."
        
        if recent_events:
            context_summary += " Recent events: " + "; ".join([
                f"took {len(event.get('actions', []))} actions ({', '.join(event.get('actions', [])[:2])}{'...' if len(event.get('actions', [])) > 2 else ''})"
                for event in recent_events[-2:]
            ])
        
        style_description = self.narration_styles.get(style, "engaging and entertaining")
        
        prompt = f"""You are a Pokemon adventure narrator creating entertaining commentary for streaming audiences.

CONTEXT:
{context_summary}

CURRENT ACTION:
- Player took actions: {player_response.get('actions', [])}
- Current situation: {player_response.get('current_situation', 'exploring')}
- AI reasoning: {player_response.get('action_reasoning', 'continuing adventure')}

DETECTED DIALOGUE (if any):
{player_response.get('detected_dialogue', 'None')}

NARRATION STYLE: {style_description}

Generate a brief, entertaining narration (2-3 sentences max) that:
1. Describes what's happening in an engaging way
2. If there's dialogue, read it in a character voice  
3. Maintains excitement and entertainment value
4. Uses Pokemon terminology when appropriate

RESPONSE FORMAT:
Narration: [Your entertaining commentary here]
Dialogue: [Character voice reading of any dialogue, or "None"]
Scene: [Brief scene description for context]
Energy: [low/neutral/high/epic based on action intensity]

Keep it fun, engaging, and suitable for streaming audiences!"""
        
        return prompt
    
    def _parse_narration_response(self, response_text: str, style: str) -> NarrationResponse:
        """Parse Gemini's response into structured narration data"""
        
        try:
            lines = response_text.strip().split('\n')
            
            narration = ""
            dialogue = ""
            scene = ""
            energy = "neutral"
            
            # Parse structured response
            for line in lines:
                line = line.strip()
                if line.startswith("Narration:"):
                    narration = line[10:].strip()
                elif line.startswith("Dialogue:"):
                    dialogue = line[9:].strip()
                    if dialogue.lower() in ["none", "n/a", ""]:
                        dialogue = ""
                elif line.startswith("Scene:"):
                    scene = line[6:].strip()
                elif line.startswith("Energy:"):
                    energy = line[7:].strip().lower()
                elif not any(line.startswith(prefix) for prefix in ["Narration:", "Dialogue:", "Scene:", "Energy:"]):
                    # Unstructured response - use as narration
                    if not narration and line:
                        narration = line
            
            # Fallback if parsing failed
            if not narration:
                narration = response_text.strip()
            
            # Validate energy level
            if energy not in ["low", "neutral", "high", "epic"]:
                energy = "neutral"
            
            return NarrationResponse(
                success=True,
                narration=narration,
                dialogue_reading=dialogue,
                scene_description=scene,
                excitement_level=energy
            )
            
        except Exception as e:
            print(f"⚠️ NarrationAgent: Failed to parse response, using raw text: {e}")
            return NarrationResponse(
                success=True,
                narration=response_text.strip() if response_text else "The adventure continues...",
                excitement_level="neutral"
            )
    
    def _get_fallback_narration(self, game_context: Dict[str, Any]) -> str:
        """Generate fallback narration when AI fails"""
        
        fallback_lines = [
            "Our hero presses onward through the Pokemon world...",
            "The adventure takes an unexpected turn...",
            "What will happen next in this Pokemon journey?",
            "The trainer continues their quest with determination...",
            "Another step forward in this grand adventure..."
        ]
        
        import random
        return random.choice(fallback_lines)
    
    def reset_session(self):
        """Reset session-based context when game session ends"""
        self.session_context = {
            "recent_events": [],
            "character_state": {},
            "ongoing_narrative": "",
            "dialogue_history": []
        }
        print("🔄 NarrationAgent session reset")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from database"""
        try:
            from .models import Configuration
            config_obj = Configuration.get_config()
            return config_obj.to_dict() if config_obj else None
        except Exception as e:
            print(f"⚠️ NarrationAgent: Error loading configuration: {e}")
            return None
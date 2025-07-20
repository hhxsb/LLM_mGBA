#!/usr/bin/env python3
"""
Base prompt template system for game-agnostic prompt management.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import os
import time
from .base_game_engine import GameState

class BasePromptTemplate(ABC):
    """Abstract base class for game-specific prompt templates."""
    
    def __init__(self, template_path: str, game_name: str):
        self.template_path = template_path
        self.game_name = game_name
        self.template_content = ""
        self.last_modified = 0
        self.load_template()
    
    def load_template(self):
        """Load the prompt template from file."""
        try:
            if os.path.exists(self.template_path):
                with open(self.template_path, 'r') as f:
                    self.template_content = f.read()
                self.last_modified = os.path.getmtime(self.template_path)
            else:
                self.template_content = self.get_default_template()
        except Exception as e:
            print(f"Error loading template: {e}")
            self.template_content = self.get_default_template()
    
    def check_for_updates(self) -> bool:
        """Check if template file has been updated."""
        try:
            if os.path.exists(self.template_path):
                current_modified = os.path.getmtime(self.template_path)
                if current_modified > self.last_modified:
                    self.load_template()
                    return True
        except Exception as e:
            print(f"Error checking template updates: {e}")
        return False
    
    @abstractmethod
    def get_default_template(self) -> str:
        """Get the default template content for this game."""
        pass
    
    @abstractmethod
    def get_base_context_variables(self) -> Dict[str, str]:
        """Get base context variables that all prompts should have."""
        pass
    
    @abstractmethod
    def get_game_specific_variables(self, game_state: GameState, **kwargs) -> Dict[str, str]:
        """Get game-specific variables for template formatting."""
        pass
    
    def format_template(self, game_state: GameState, **kwargs) -> str:
        """Format the template with current game state and context."""
        # Get base variables
        variables = self.get_base_context_variables()
        
        # Add game-specific variables
        variables.update(self.get_game_specific_variables(game_state, **kwargs))
        
        # Add any additional variables passed in
        variables.update(kwargs)
        
        try:
            return self.template_content.format(**variables)
        except KeyError as e:
            print(f"Warning: Missing template variable {e}")
            return self.template_content
    
    def get_system_message(self) -> str:
        """Get the system message for the LLM."""
        return f"You are an AI playing {self.game_name}. Follow the instructions carefully."
    
    @abstractmethod
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get the tools available for this game."""
        pass


class Tool:
    """Simple class to define a tool for the LLM"""
    def __init__(self, name: str, description: str, parameters: List[Dict[str, Any]]):
        self.name = name
        self.description = description
        self.parameters = parameters
    
    def to_gemini_format(self) -> Dict[str, Any]:
        """Convert to Gemini's expected format"""
        properties = {}
        for p in self.parameters:
            prop = {
                "type": p["type"],
                "description": p["description"]
            }
            # Handle array types with items
            if p["type"] == "array" and "items" in p:
                prop["items"] = p["items"]
            # Handle enum values
            if "enum" in p:
                prop["enum"] = p["enum"]
            properties[p["name"]] = prop
        
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": [p["name"] for p in self.parameters if p.get("required", False)]
            }
        }
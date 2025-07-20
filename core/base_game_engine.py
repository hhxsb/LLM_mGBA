#!/usr/bin/env python3
"""
Abstract base class for game-specific engines.
Each game implementation should inherit from BaseGameEngine.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass

@dataclass
class GameState:
    """Represents the current state of the game."""
    player_x: int = 0
    player_y: int = 0
    player_direction: str = "UNKNOWN"
    map_id: int = 0
    additional_data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.additional_data is None:
            self.additional_data = {}

@dataclass
class ButtonAction:
    """Represents a button action with optional duration."""
    button: str
    duration: int = 2  # Default 2 frames
    
class BaseGameEngine(ABC):
    """Abstract base class for game-specific engines."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.button_map = self._get_button_map()
    
    @abstractmethod
    def _get_button_map(self) -> Dict[str, int]:
        """Return the mapping of button names to button codes for this game."""
        pass
    
    @abstractmethod
    def get_map_name(self, map_id: int) -> str:
        """Get human-readable map name from map ID."""
        pass
    
    @abstractmethod
    def parse_game_state(self, state_data: List[str]) -> GameState:
        """Parse raw game state data from emulator into GameState object."""
        pass
    
    @abstractmethod
    def get_navigation_guidance(self, game_state: GameState) -> str:
        """Get game-specific navigation guidance text."""
        pass
    
    @abstractmethod
    def get_game_objectives(self) -> List[str]:
        """Get the main objectives for this game."""
        pass
    
    @abstractmethod
    def validate_button_sequence(self, buttons: List[str]) -> List[str]:
        """Validate and filter button sequence for this game."""
        pass
    
    @abstractmethod
    def get_memory_addresses(self) -> Dict[str, int]:
        """Get memory addresses for reading game state (if applicable)."""
        pass
    
    def convert_buttons_to_codes(self, buttons: List[str]) -> List[int]:
        """Convert button names to codes using the game's button map."""
        codes = []
        for button in buttons:
            button = button.upper()
            if button in self.button_map:
                codes.append(self.button_map[button])
        return codes
    
    def get_available_buttons(self) -> List[str]:
        """Get list of all available button names for this game."""
        return list(self.button_map.keys())
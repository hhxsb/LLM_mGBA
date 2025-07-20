#!/usr/bin/env python3
"""
Pokemon Red specific game engine implementation.
"""

from typing import Dict, List, Any
import sys
import os

# Add parent directories to path to import core modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from core.base_game_engine import BaseGameEngine, GameState


class PokemonRedGameEngine(BaseGameEngine):
    """Game engine specifically for Pokemon Red."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # Pokemon Red specific initialization
        self.map_names = self._initialize_map_names()
    
    def _get_button_map(self) -> Dict[str, int]:
        """Return the GBA button mapping for Pokemon Red."""
        return {
            "A": 0, "B": 1, "SELECT": 2, "START": 3,
            "RIGHT": 4, "LEFT": 5, "UP": 6, "DOWN": 7,
            "R": 8, "L": 9
        }
    
    def _initialize_map_names(self) -> Dict[int, str]:
        """Initialize Pokemon Red map ID to name mapping."""
        return {
            0: "Pallet Town",
            1: "Viridian City", 
            2: "Pewter City",
            3: "Cerulean City",
            4: "Vermillion City",
            5: "Lavender Town",
            6: "Celadon City",
            7: "Fuchsia City",
            8: "Cinnabar Island",
            9: "Indigo Plateau",
            10: "Saffron City",
            11: "Unknown Area",
            12: "Route 1",
            13: "Route 2", 
            14: "Route 3",
            15: "Route 4",
            16: "Route 5",
            17: "Route 6",
            18: "Route 7",
            19: "Route 8",
            20: "Route 9",
            21: "Route 10",
            22: "Route 11",
            23: "Route 12",
            24: "Route 13",
            25: "Route 14",
            26: "Route 15",
            27: "Route 16",
            28: "Route 17",
            29: "Route 18",
            30: "Route 19",
            31: "Route 20",
            32: "Route 21",
            33: "Route 22",
            34: "Route 23",
            35: "Route 24",
            36: "Route 25",
            37: "Red's House 1F",
            38: "Red's House 2F", 
            39: "Blue's House",
            40: "Oak's Lab",
            41: "Viridian City Pokémon Center",
            42: "Viridian City Mart",
            43: "Trainer School",
            44: "Viridian City Gym",
            45: "Digletts Cave",
            46: "Viridian Forest",
            47: "Pewter City Museum",
            48: "Pewter City Gym",
            49: "Pewter City Pokémon Center",
            50: "Pewter City Mart",
            # Add more map IDs as discovered during gameplay
        }
    
    def get_map_name(self, map_id: int) -> str:
        """Get human-readable map name from map ID."""
        return self.map_names.get(map_id, f"Unknown Area (Map ID: {map_id})")
    
    def parse_game_state(self, state_data: List[str]) -> GameState:
        """Parse Pokemon Red game state from emulator data."""
        if len(state_data) >= 4:
            try:
                player_direction = state_data[0]
                player_x = int(state_data[1])
                player_y = int(state_data[2])
                map_id = int(state_data[3])
                
                return GameState(
                    player_x=player_x,
                    player_y=player_y,
                    player_direction=player_direction,
                    map_id=map_id
                )
            except (ValueError, IndexError) as e:
                print(f"Error parsing game state: {e}")
        
        return GameState()  # Return default state on error
    
    def get_navigation_guidance(self, game_state: GameState) -> str:
        """Get Pokemon Red specific navigation guidance."""
        directions = {
            "UP": "north",
            "DOWN": "south", 
            "LEFT": "west",
            "RIGHT": "east"
        }
        
        facing_direction = directions.get(game_state.player_direction, game_state.player_direction)
        
        guidance = f"""
## Navigation Tips for Pokémon:
- To INTERACT with NPCs or objects, you MUST be FACING them and then press A
- Your current direction is {game_state.player_direction} (facing {facing_direction})
- Your current position is (X={game_state.player_x}, Y={game_state.player_y}) on map {game_state.map_id}
- If you need to face a different direction, press the appropriate directional button first
- In buildings, look for exits via stairs, doors, or red mats and walk directly over them
- To enter/exit buildings, walk directly onto doors, stairs, or exit mats
- Red mats typically indicate exits in buildings
- Black/gray areas are walls - you cannot walk through them
"""
        
        return guidance
    
    def get_game_objectives(self) -> List[str]:
        """Get Pokemon Red main objectives."""
        return [
            "Beat the Elite Four and become Champion",
            "Collect all 150 Pokémon",
            "Defeat all 8 Gym Leaders",
            "Complete the Pokédex",
            "Explore all regions and routes"
        ]
    
    def convert_button_names_to_codes(self, button_names: List[str]) -> List[int]:
        """Convert button names to their numeric codes."""
        button_codes = []
        
        for button in button_names:
            button_upper = button.upper()
            if button_upper in self.button_map:
                button_codes.append(self.button_map[button_upper])
            else:
                print(f"Warning: Invalid button '{button}' ignored")
        
        return button_codes
    
    def validate_button_sequence(self, buttons: List[str]) -> List[str]:
        """Validate and filter button sequence for Pokemon Red."""
        valid_buttons = []
        button_names = list(self.button_map.keys())
        
        for button in buttons:
            button = button.upper()
            if button in button_names:
                valid_buttons.append(button)
            else:
                print(f"Warning: Invalid button '{button}' ignored")
        
        return valid_buttons
    
    def get_memory_addresses(self) -> Dict[str, int]:
        """Get Pokemon Red memory addresses for reading game state."""
        return {
            'player_x': 0xD362,
            'player_y': 0xD361, 
            'player_direction': 0xD363,
            'map_id': 0xD35E,
            'player_name': 0xD158,
            'money': 0xD347,
            'badges': 0xD356,
            'pokedex_owned': 0xD2F7,
            'pokedex_seen': 0xD30A,
            # Add more addresses as needed
        }
    
    def is_in_battle(self, game_state: GameState) -> bool:
        """Check if currently in a Pokemon battle (would need memory reading)."""
        # This would require reading battle state from memory
        # For now, return False as placeholder
        return False
    
    def is_in_menu(self, game_state: GameState) -> bool:
        """Check if currently in a menu (would need memory reading)."""
        # This would require reading menu state from memory  
        # For now, return False as placeholder
        return False
    
    def get_pokemon_team_info(self) -> Dict[str, Any]:
        """Get current Pokemon team information (would need memory reading)."""
        # This would require reading Pokemon data from memory
        # For now, return empty dict as placeholder
        return {}
    
    def get_inventory_info(self) -> Dict[str, Any]:
        """Get current inventory information (would need memory reading)."""
        # This would require reading inventory data from memory
        # For now, return empty dict as placeholder
        return {}
"""
Game Detection Service
Handles automatic game detection and provides game configuration management.
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class GameConfig:
    """Configuration for a specific game"""
    id: str
    name: str
    platform: str
    memory_type: str  # "static" or "dynamic"
    memory_addresses: Dict[str, Optional[int]]
    direction_encoding: Dict[int, str]
    fallback_addresses: List[Dict[str, int]] = None


class GameDetector:
    """Detects games and provides configuration"""
    
    def __init__(self):
        self.games = self._initialize_game_configs()
        self.manual_override = None
    
    def _initialize_game_configs(self) -> Dict[str, GameConfig]:
        """Initialize all supported game configurations"""
        games = {}
        
        # Pokemon Red/Blue
        games["pokemon_red"] = GameConfig(
            id="pokemon_red",
            name="Pokémon Red/Blue",
            platform="Game Boy",
            memory_type="static",
            memory_addresses={
                "playerDirection": 0xC109,
                "playerX": 0xD362,
                "playerY": 0xD361,
                "mapId": 0xD35E,
            },
            direction_encoding={
                0: "DOWN",
                4: "UP", 
                8: "LEFT",
                12: "RIGHT"
            }
        )
        
        # Pokemon Sapphire
        games["pokemon_sapphire"] = GameConfig(
            id="pokemon_sapphire",
            name="Pokémon Sapphire",
            platform="Game Boy Advance",
            memory_type="dynamic",
            memory_addresses={
                "playerDirection": None,
                "playerX": None,
                "playerY": None,
                "mapId": None,
            },
            direction_encoding={
                1: "DOWN",
                2: "UP",
                3: "LEFT", 
                4: "RIGHT"
            },
            fallback_addresses=[
                {
                    "playerX": 0x02031DBC,
                    "playerY": 0x02031DBE,
                    "playerDirection": 0x02031DC0,
                    "mapId": 0x02031DC2,
                },
                {
                    "playerX": 0x02024EA4,
                    "playerY": 0x02024EA6,
                    "playerDirection": 0x02024EA8,
                    "mapId": 0x02024EAA,
                },
                {
                    "playerX": 0x02037BA8,
                    "playerY": 0x02037BAA,
                    "playerDirection": 0x02037BAC,
                    "mapId": 0x02037BAE,
                }
            ]
        )
        
        # Pokemon Ruby
        games["pokemon_ruby"] = GameConfig(
            id="pokemon_ruby",
            name="Pokémon Ruby",
            platform="Game Boy Advance",
            memory_type="dynamic",
            memory_addresses={
                "playerDirection": None,
                "playerX": None,
                "playerY": None,
                "mapId": None,
            },
            direction_encoding={
                1: "DOWN",
                2: "UP",
                3: "LEFT",
                4: "RIGHT"
            },
            fallback_addresses=[
                {
                    "playerX": 0x02031DBC,
                    "playerY": 0x02031DBE,
                    "playerDirection": 0x02031DC0,
                    "mapId": 0x02031DC2,
                },
                {
                    "playerX": 0x02024EA4,
                    "playerY": 0x02024EA6,
                    "playerDirection": 0x02024EA8,
                    "mapId": 0x02024EAA,
                }
            ]
        )
        
        # Pokemon Emerald
        games["pokemon_emerald"] = GameConfig(
            id="pokemon_emerald",
            name="Pokémon Emerald",
            platform="Game Boy Advance",
            memory_type="dynamic",
            memory_addresses={
                "playerDirection": None,
                "playerX": None,
                "playerY": None,
                "mapId": None,
            },
            direction_encoding={
                1: "DOWN",
                2: "UP",
                3: "LEFT",
                4: "RIGHT"
            },
            fallback_addresses=[
                {
                    "playerX": 0x02031E40,
                    "playerY": 0x02031E42,
                    "playerDirection": 0x02031E44,
                    "mapId": 0x02031E46,
                }
            ]
        )
        
        # Pokemon FireRed
        games["pokemon_firered"] = GameConfig(
            id="pokemon_firered",
            name="Pokémon FireRed",
            platform="Game Boy Advance",
            memory_type="dynamic",
            memory_addresses={
                "playerDirection": None,
                "playerX": None,
                "playerY": None,
                "mapId": None,
            },
            direction_encoding={
                1: "DOWN",
                2: "UP",
                3: "LEFT",
                4: "RIGHT"
            },
            fallback_addresses=[
                {
                    "playerX": 0x02024C68,
                    "playerY": 0x02024C6A,
                    "playerDirection": 0x02024C6C,
                    "mapId": 0x02024C6E,
                }
            ]
        )
        
        # Pokemon LeafGreen
        games["pokemon_leafgreen"] = GameConfig(
            id="pokemon_leafgreen",
            name="Pokémon LeafGreen",
            platform="Game Boy Advance",
            memory_type="dynamic",
            memory_addresses={
                "playerDirection": None,
                "playerX": None,
                "playerY": None,
                "mapId": None,
            },
            direction_encoding={
                1: "DOWN",
                2: "UP",
                3: "LEFT",
                4: "RIGHT"
            },
            fallback_addresses=[
                {
                    "playerX": 0x02024C68,
                    "playerY": 0x02024C6A,
                    "playerDirection": 0x02024C6C,
                    "mapId": 0x02024C6E,
                }
            ]
        )
        
        return games
    
    def detect_game_from_rom_name(self, rom_name: str) -> Optional[str]:
        """Detect game from ROM name using pattern matching"""
        if not rom_name:
            return None
        
        rom_upper = rom_name.upper()
        
        # Detection patterns - order matters for specificity
        patterns = [
            (r"POKEMON.*SAPPHIRE", "pokemon_sapphire"),
            (r"POKEMON.*RUBY", "pokemon_ruby"),
            (r"POKEMON.*EMERALD", "pokemon_emerald"),
            (r"POKEMON.*FIRERED", "pokemon_firered"),
            (r"POKEMON.*LEAFGREEN", "pokemon_leafgreen"),
            (r"POKEMON.*RED", "pokemon_red"),
            (r"POKEMON.*BLUE", "pokemon_red"),  # Blue uses same config as Red
        ]
        
        for pattern, game_id in patterns:
            if re.search(pattern, rom_upper):
                return game_id
        
        return None
    
    def detect_game_from_path(self, rom_path: str) -> Optional[str]:
        """Detect game from ROM file path"""
        if not rom_path:
            return None
        
        # Extract filename from path
        import os
        filename = os.path.basename(rom_path).upper()
        
        # Remove common extensions
        for ext in ['.GBA', '.GB', '.GBC', '.ZIP', '.7Z']:
            if filename.endswith(ext):
                filename = filename[:-len(ext)]
                break
        
        return self.detect_game_from_rom_name(filename)
    
    def set_manual_override(self, game_id: str) -> bool:
        """Set manual game override"""
        if game_id in self.games:
            self.manual_override = game_id
            print(f"🎮 Game manually set to: {self.games[game_id].name}")
            return True
        return False
    
    def clear_manual_override(self):
        """Clear manual game override"""
        self.manual_override = None
        
        # Also clear database override
        try:
            from .models import Configuration
            config = Configuration.get_config()
            if config.game_override:
                config.game_override = ''
                config.detection_source = 'auto'
                config.save()
                print("🎮 Manual game override cleared from database")
            else:
                print("🎮 Manual game override cleared (was already clear in database)")
        except Exception as e:
            print(f"⚠️ Error clearing database override: {e}")
    
    def get_current_game(self, rom_name: str = None, rom_path: str = None) -> Tuple[Optional[str], str]:
        """
        Get current game ID and detection source
        
        Returns:
            (game_id, source) where source is "manual", "rom_name", "rom_path", or "default"
        """
        # Check database for manual override first
        try:
            from .models import Configuration
            config = Configuration.get_config()
            if config.game_override:
                print(f"🔍 Using database manual override: {config.game_override}")
                self.manual_override = config.game_override
                return config.game_override, "manual"
        except Exception as e:
            print(f"⚠️ Error checking database override: {e}")
        
        # Manual override takes priority
        if self.manual_override:
            print(f"🔍 Using in-memory manual override: {self.manual_override}")
            return self.manual_override, "manual"
        
        # Try ROM name detection
        if rom_name:
            detected = self.detect_game_from_rom_name(rom_name)
            if detected:
                print(f"🔍 ROM name detection successful: {rom_name} -> {detected}")
                return detected, "rom_name"
        
        # Try ROM path detection
        if rom_path:
            detected = self.detect_game_from_path(rom_path)
            if detected:
                print(f"🔍 ROM path detection successful: {rom_path} -> {detected}")
                return detected, "rom_path"
        
        # Default fallback
        print(f"🔍 Using default fallback: pokemon_red")
        return "pokemon_red", "default"
    
    def get_game_config(self, game_id: str) -> Optional[GameConfig]:
        """Get configuration for a specific game"""
        return self.games.get(game_id)
    
    def get_all_games(self) -> List[Dict[str, str]]:
        """Get list of all supported games for UI dropdown"""
        return [
            {"id": game.id, "name": game.name, "platform": game.platform}
            for game in self.games.values()
        ]
    
    def format_game_config_for_lua(self, game_id: str) -> Optional[str]:
        """Format game configuration as Lua table string for transmission to mGBA"""
        config = self.get_game_config(game_id)
        if not config:
            return None
        
        # Format memory addresses
        addresses_str = "{"
        for key, value in config.memory_addresses.items():
            if value is not None:
                addresses_str += f'{key}=0x{value:08X},'
            else:
                addresses_str += f'{key}=nil,'
        addresses_str = addresses_str.rstrip(',') + "}"
        
        # Format direction encoding
        directions_str = "{"
        for key, value in config.direction_encoding.items():
            directions_str += f'[{key}]="{value}",'
        directions_str = directions_str.rstrip(',') + "}"
        
        # Format fallback addresses if present
        fallback_str = "nil"
        if config.fallback_addresses:
            fallback_str = "{"
            for i, addr_set in enumerate(config.fallback_addresses):
                fallback_str += "{"
                for key, value in addr_set.items():
                    fallback_str += f'{key}=0x{value:08X},'
                fallback_str = fallback_str.rstrip(',') + "},"
            fallback_str = fallback_str.rstrip(',') + "}"
        
        lua_config = f"""{{
    id="{config.id}",
    name="{config.name}",
    platform="{config.platform}",
    memoryType="{config.memory_type}",
    memoryAddresses={addresses_str},
    directionEncoding={directions_str},
    fallbackAddresses={fallback_str}
}}"""
        
        return lua_config


# Global detector instance
_game_detector = None

def get_game_detector() -> GameDetector:
    """Get the global game detector instance"""
    global _game_detector
    if _game_detector is None:
        _game_detector = GameDetector()
    return _game_detector
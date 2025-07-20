#!/usr/bin/env python3
"""
Game registry and factory system for dynamic loading of game modules.
"""

from typing import Dict, Type, Any, Optional
import importlib
import importlib.util
import os
from .base_game_controller import BaseGameController


class GameRegistry:
    """Registry for available games and their controllers."""
    
    def __init__(self):
        self._games: Dict[str, Dict[str, Any]] = {}
        self._discover_games()
    
    def _discover_games(self):
        """Automatically discover available games in the games directory."""
        games_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'games')
        
        if not os.path.exists(games_dir):
            return
        
        for item in os.listdir(games_dir):
            game_path = os.path.join(games_dir, item)
            if os.path.isdir(game_path) and not item.startswith('__'):
                self._try_register_game(item, game_path)
    
    def _try_register_game(self, game_name: str, game_path: str):
        """Try to register a game from its directory."""
        try:
            # Look for game_info.py or controller.py
            info_file = os.path.join(game_path, 'game_info.py')
            controller_file = os.path.join(game_path, 'controller.py')
            
            if os.path.exists(info_file):
                # Load game info
                spec = importlib.util.spec_from_file_location(f"{game_name}_info", info_file)
                info_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(info_module)
                
                if hasattr(info_module, 'GAME_INFO'):
                    game_info = info_module.GAME_INFO
                    game_info['module_path'] = game_path
                    game_info['controller_file'] = controller_file
                    self._games[game_name] = game_info
                    print(f"Registered game: {game_name}")
            
        except Exception as e:
            print(f"Failed to register game {game_name}: {e}")
    
    def register_game(self, name: str, controller_class: Type[BaseGameController], 
                     description: str = "", version: str = "1.0"):
        """Manually register a game."""
        self._games[name] = {
            'name': name,
            'description': description,
            'version': version,
            'controller_class': controller_class
        }
    
    def get_game_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get information about a registered game."""
        return self._games.get(name)
    
    def list_games(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered games."""
        return self._games.copy()
    
    def is_game_available(self, name: str) -> bool:
        """Check if a game is available."""
        return name in self._games


class GameFactory:
    """Factory for creating game controller instances."""
    
    def __init__(self, registry: GameRegistry):
        self.registry = registry
    
    def create_controller(self, game_name: str, config: Dict[str, Any]) -> BaseGameController:
        """Create a controller instance for the specified game."""
        game_info = self.registry.get_game_info(game_name)
        
        if not game_info:
            raise ValueError(f"Game '{game_name}' is not registered")
        
        # If controller_class is directly available
        if 'controller_class' in game_info:
            controller_class = game_info['controller_class']
            return controller_class(config)
        
        # If we need to load from file
        if 'controller_file' in game_info and os.path.exists(game_info['controller_file']):
            return self._load_controller_from_file(game_info['controller_file'], config)
        
        raise ValueError(f"Cannot create controller for game '{game_name}': missing controller implementation")
    
    def _load_controller_from_file(self, controller_file: str, config: Dict[str, Any]) -> BaseGameController:
        """Load controller class from file and create instance."""
        try:
            # Extract module name from file path
            module_name = os.path.splitext(os.path.basename(controller_file))[0]
            
            # Load the module
            spec = importlib.util.spec_from_file_location(module_name, controller_file)
            controller_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(controller_module)
            
            # Look for a controller class (should inherit from BaseGameController)
            controller_class = None
            for attr_name in dir(controller_module):
                attr = getattr(controller_module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, BaseGameController) and 
                    attr != BaseGameController):
                    controller_class = attr
                    break
            
            if not controller_class:
                raise ValueError(f"No valid controller class found in {controller_file}")
            
            return controller_class(config)
            
        except Exception as e:
            raise ValueError(f"Failed to load controller from {controller_file}: {e}")


# Global registry instance
_global_registry = GameRegistry()

def get_game_registry() -> GameRegistry:
    """Get the global game registry."""
    return _global_registry

def create_game_controller(game_name: str, config: Dict[str, Any]) -> BaseGameController:
    """Convenience function to create a game controller."""
    factory = GameFactory(_global_registry)
    return factory.create_controller(game_name, config)
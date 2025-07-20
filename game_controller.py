#!/usr/bin/env python3
"""
Main entry point for the modular LLM Game AI system.
"""

import argparse
import json
import sys
import os
from typing import Dict, Any

# Import the game registry and factory
from core.game_registry import GameRegistry, GameFactory, get_game_registry, create_game_controller


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from JSON file."""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"Failed to load config from {config_path}: {e}")
        sys.exit(1)


def list_available_games():
    """List all available games."""
    registry = get_game_registry()
    games = registry.list_games()
    
    if not games:
        print("No games are currently registered.")
        return
    
    print("Available games:")
    print("-" * 50)
    for game_name, game_info in games.items():
        display_name = game_info.get('display_name', game_name)
        description = game_info.get('description', 'No description available')
        version = game_info.get('version', 'Unknown version')
        
        print(f"Game: {display_name} ({game_name})")
        print(f"  Description: {description}")
        print(f"  Version: {version}")
        
        if 'platform' in game_info:
            print(f"  Platform: {game_info['platform']}")
        
        if 'supported_features' in game_info:
            features = ", ".join(game_info['supported_features'])
            print(f"  Features: {features}")
        
        print()


def validate_game_config(game_name: str, config: Dict[str, Any]) -> bool:
    """Validate that the configuration has necessary settings for the game."""
    registry = get_game_registry()
    game_info = registry.get_game_info(game_name)
    
    if not game_info:
        print(f"Error: Game '{game_name}' is not registered.")
        return False
    
    # Check for required API keys
    requirements = game_info.get('requirements', {})
    api_keys = requirements.get('api_keys', [])
    
    for api_key in api_keys:
        if api_key == 'google_gemini':
            if not config.get('providers', {}).get('google', {}).get('api_key'):
                print(f"Error: Google Gemini API key is required for {game_name}")
                return False
        elif api_key == 'openai':
            if not config.get('providers', {}).get('openai', {}).get('api_key'):
                print(f"Error: OpenAI API key is required for {game_name}")
                return False
        elif api_key == 'anthropic':
            if not config.get('providers', {}).get('anthropic', {}).get('api_key'):
                print(f"Error: Anthropic API key is required for {game_name}")
                return False
    
    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="LLM Game AI - Modular system for playing GBA games with AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --game pokemon_red --config config.json
  %(prog)s --list-games
  %(prog)s --game pokemon_red --config my_config.json --debug
        """
    )
    
    parser.add_argument("--game", "-g", 
                        help="Name of the game to play (use --list-games to see available games)")
    parser.add_argument("--config", "-c", 
                        default="config.json",
                        help="Path to the configuration file (default: config.json)")
    parser.add_argument("--list-games", 
                        action="store_true",
                        help="List all available games and exit")
    parser.add_argument("--debug", 
                        action="store_true",
                        help="Enable debug mode")
    
    args = parser.parse_args()
    
    # Handle list games command
    if args.list_games:
        list_available_games()
        return
    
    # Validate arguments
    if not args.game:
        print("Error: --game argument is required (use --list-games to see available games)")
        parser.print_help()
        sys.exit(1)
    
    # Load configuration
    config = load_config(args.config)
    
    # Override debug mode if specified
    if args.debug:
        config['debug_mode'] = True
    
    # Validate game and config compatibility
    if not validate_game_config(args.game, config):
        sys.exit(1)
    
    # Create and start the game controller
    try:
        print(f"Starting {args.game} controller...")
        controller = create_game_controller(args.game, config)
        controller.start()
        
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error starting game controller: {e}")
        if config.get('debug_mode', False):
            import traceback
            print(traceback.format_exc())
        sys.exit(1)
    finally:
        # Cleanup would be handled by the controller's cleanup method
        pass


if __name__ == "__main__":
    main()
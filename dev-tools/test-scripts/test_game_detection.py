#!/usr/bin/env python3
"""
Test script for Python-based game detection system
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_gba_player.settings')
sys.path.append('/Users/chengwan/Projects/pokemonAI/LLM-Pokemon-Red/ai_gba_player')
django.setup()

from dashboard.game_detector import get_game_detector

def test_game_detection():
    """Test the game detection system"""
    print("🧪 Testing Python-based Game Detection System\n")
    
    # Get game detector instance
    detector = get_game_detector()
    
    # Test 1: ROM name detection
    print("=== Test 1: ROM Name Detection ===")
    test_names = [
        "Pokemon Sapphire Version",
        "POKEMON RUBY VERSION", 
        "Pokemon Red Version",
        "pokemon_emerald_u.gba",
        "Pokemon FireRed (U).gba",
        "Unknown Game.gba"
    ]
    
    for rom_name in test_names:
        detected = detector.detect_game_from_rom_name(rom_name)
        print(f"ROM: '{rom_name}' -> {detected}")
    
    # Test 2: ROM path detection
    print("\n=== Test 2: ROM Path Detection ===")
    test_paths = [
        "/roms/pokemon_sapphire.gba",
        "/games/Ruby Version (U).gba",
        "/files/emerald_version.zip",
        "/path/unknown_game.gba"
    ]
    
    for rom_path in test_paths:
        detected = detector.detect_game_from_path(rom_path)
        print(f"Path: '{rom_path}' -> {detected}")
    
    # Test 3: Current game detection with precedence
    print("\n=== Test 3: Current Game Detection (with precedence) ===")
    
    # Test auto detection
    game_id, source = detector.get_current_game(rom_name="Pokemon Sapphire Version")
    print(f"Auto detection: {game_id} (source: {source})")
    
    # Test manual override
    detector.set_manual_override("pokemon_emerald")
    game_id, source = detector.get_current_game(rom_name="Pokemon Sapphire Version")
    print(f"With manual override: {game_id} (source: {source})")
    
    # Clear override
    detector.clear_manual_override()
    game_id, source = detector.get_current_game(rom_name="Pokemon Sapphire Version")
    print(f"After clearing override: {game_id} (source: {source})")
    
    # Test 4: Game configurations
    print("\n=== Test 4: Game Configurations ===")
    games = detector.get_all_games()
    print(f"Total supported games: {len(games)}")
    for game in games:
        print(f"  - {game['name']} ({game['platform']}) [ID: {game['id']}]")
    
    # Test 5: Lua configuration formatting
    print("\n=== Test 5: Lua Configuration Formatting ===")
    sapphire_config = detector.format_game_config_for_lua("pokemon_sapphire")
    if sapphire_config:
        print("Pokemon Sapphire Lua config (first 200 chars):")
        print(sapphire_config[:200] + "..." if len(sapphire_config) > 200 else sapphire_config)
    else:
        print("❌ Failed to format Sapphire config")
    
    print("\n✅ Game detection tests completed!")

if __name__ == "__main__":
    test_game_detection()
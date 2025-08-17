#!/usr/bin/env python3
"""
Test Pokemon Sapphire detection with real ROM path
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_gba_player.settings')
sys.path.append('/Users/chengwan/Projects/pokemonAI/LLM-Pokemon-Red/ai_gba_player')
django.setup()

from dashboard.game_detector import get_game_detector
from dashboard.models import Configuration

def test_sapphire_detection():
    print("🧪 Testing Pokemon Sapphire Detection\n")
    
    detector = get_game_detector()
    config = Configuration.get_config()
    
    print("=== Current Configuration ===")
    print(f"ROM Path: {config.rom_path}")
    print(f"ROM Display Name: '{config.rom_display_name}'")
    print(f"Current Game: {config.game}")
    print(f"Detected Game: {config.detected_game}")
    print(f"Manual Override: '{config.game_override}'")
    print(f"Detection Source: {config.detection_source}")
    
    print("\n=== Testing Detection Logic ===")
    
    # Test various Sapphire ROM name patterns
    test_names = [
        "Pokemon Sapphire Version",
        "POKEMON SAPPHIRE", 
        "pokemon_sapphire",
        "Pokemon Sapphire (U)",
        "pokemon sapphire.gba"
    ]
    
    for name in test_names:
        detected = detector.detect_game_from_rom_name(name)
        print(f"Name '{name}' -> {detected}")
    
    print("\n=== Testing Path Detection ===")
    test_paths = [
        "/path/pokemon_sapphire.gba",
        "/roms/Pokemon_Sapphire_Version.gba",
        "/games/sapphire.gba",
        config.rom_path  # Current configured path
    ]
    
    for path in test_paths:
        detected = detector.detect_game_from_path(path)
        print(f"Path '{path}' -> {detected}")
    
    print("\n=== Current Game Detection ===")
    game_id, source = detector.get_current_game(
        rom_name=config.rom_display_name,
        rom_path=config.rom_path
    )
    print(f"Current detection: {game_id} (source: {source})")
    
    # Get game config for Sapphire
    sapphire_config = detector.get_game_config("pokemon_sapphire")
    if sapphire_config:
        print(f"\n=== Pokemon Sapphire Config ===")
        print(f"Name: {sapphire_config.name}")
        print(f"Platform: {sapphire_config.platform}")
        print(f"Memory Type: {sapphire_config.memory_type}")
        print(f"Fallback Addresses: {len(sapphire_config.fallback_addresses) if sapphire_config.fallback_addresses else 0} sets")
    
    print("\n✅ Detection test completed!")

if __name__ == "__main__":
    test_sapphire_detection()
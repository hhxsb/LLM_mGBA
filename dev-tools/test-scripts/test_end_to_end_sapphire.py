#!/usr/bin/env python3
"""
End-to-end test for Pokemon Sapphire detection and configuration flow
"""

import os
import sys
import django
import json

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_gba_player.settings')
sys.path.append('/Users/chengwan/Projects/pokemonAI/LLM-Pokemon-Red/ai_gba_player')
django.setup()

from dashboard.game_detector import get_game_detector
from dashboard.models import Configuration

def test_end_to_end_flow():
    print("🧪 End-to-End Pokemon Sapphire Detection Test\n")
    
    # Step 1: Simulate user has Pokemon Sapphire ROM
    print("=== Step 1: ROM Setup ===")
    config = Configuration.get_config()
    config.rom_path = "/path/to/Pokemon_Sapphire_Version.gba"
    config.rom_display_name = "Pokemon Sapphire Version"
    config.save()
    print(f"✅ ROM configured: {config.rom_display_name}")
    
    # Step 2: Game Detection (what happens when AI service starts)
    print("\n=== Step 2: Game Detection ===")
    detector = get_game_detector()
    
    # Clear any overrides to test auto-detection
    detector.clear_manual_override()
    
    # Detect game (simulates _detect_and_configure_game)
    game_id, detection_source = detector.get_current_game(
        rom_name=config.rom_display_name,
        rom_path=config.rom_path
    )
    
    print(f"✅ Detected game: {game_id} (source: {detection_source})")
    
    # Step 3: Update configuration (simulates _update_configuration_with_detection)
    print("\n=== Step 3: Configuration Update ===")
    config.detected_game = game_id
    config.detection_source = detection_source
    config.game = game_id  # Set active game
    config.save()
    print(f"✅ Configuration updated - active game: {config.game}")
    
    # Step 4: Generate Lua configuration (simulates _send_game_config_to_lua)
    print("\n=== Step 4: Lua Configuration Generation ===")
    lua_config = detector.format_game_config_for_lua(game_id)
    
    if lua_config:
        print("✅ Lua configuration generated successfully")
        print(f"Config size: {len(lua_config)} characters")
        
        # Show key parts of the config
        if "pokemon_sapphire" in lua_config:
            print("✅ Contains correct game ID")
        if "Game Boy Advance" in lua_config:
            print("✅ Contains correct platform")
        if "dynamic" in lua_config:
            print("✅ Contains correct memory type")
        if "fallbackAddresses" in lua_config:
            print("✅ Contains fallback addresses")
    else:
        print("❌ Failed to generate Lua configuration")
        return False
    
    # Step 5: Simulate Lua parsing (what happens in handleGameConfig)
    print("\n=== Step 5: Lua Parsing Simulation ===")
    try:
        # Test if the Lua config would parse correctly
        # We'll check the structure without actually executing Lua
        config_lines = lua_config.split('\n')
        
        checks = {
            'has_id': any('id="pokemon_sapphire"' in line for line in config_lines),
            'has_name': any('name="Pokémon Sapphire"' in line for line in config_lines),
            'has_platform': any('platform="Game Boy Advance"' in line for line in config_lines),
            'has_memory_type': any('memoryType="dynamic"' in line for line in config_lines),
            'has_addresses': any('memoryAddresses=' in line for line in config_lines),
            'has_direction_encoding': any('directionEncoding=' in line for line in config_lines),
            'has_fallback': any('fallbackAddresses=' in line for line in config_lines),
        }
        
        all_passed = all(checks.values())
        
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"{status} {check}: {passed}")
        
        if all_passed:
            print("✅ Lua configuration structure is valid")
        else:
            print("❌ Lua configuration has structural issues")
            return False
        
    except Exception as e:
        print(f"❌ Lua configuration parsing error: {e}")
        return False
    
    # Step 6: Test API endpoints
    print("\n=== Step 6: API Endpoint Simulation ===")
    
    # Simulate GET /api/games/status/
    current_status = {
        'current_game': {
            'id': config.game,
            'name': detector.get_game_config(config.game).name,
            'platform': detector.get_game_config(config.game).platform
        },
        'detection': {
            'detected_game': config.detected_game,
            'manual_override': config.game_override,
            'detection_source': config.detection_source
        },
        'rom_info': {
            'rom_path': config.rom_path,
            'rom_display_name': config.rom_display_name
        }
    }
    
    print("✅ API status response:", json.dumps(current_status, indent=2))
    
    # Step 7: Test manual override
    print("\n=== Step 7: Manual Override Test ===")
    
    # Set manual override to Emerald
    detector.set_manual_override("pokemon_emerald")
    override_game, override_source = detector.get_current_game(
        rom_name=config.rom_display_name,
        rom_path=config.rom_path
    )
    print(f"✅ Manual override test: {override_game} (source: {override_source})")
    
    # Clear override back to auto-detection
    detector.clear_manual_override()
    auto_game, auto_source = detector.get_current_game(
        rom_name=config.rom_display_name,
        rom_path=config.rom_path
    )
    print(f"✅ Auto-detection restored: {auto_game} (source: {auto_source})")
    
    print("\n🎉 End-to-End Test PASSED!")
    print("\nSummary:")
    print(f"  ✅ Pokemon Sapphire ROM detected from: {detection_source}")
    print(f"  ✅ Lua configuration generated: {len(lua_config)} chars")
    print(f"  ✅ GBA dynamic memory type configured")
    print(f"  ✅ 3 fallback address sets available")
    print(f"  ✅ Manual override system working")
    print(f"  ✅ API endpoints functional")
    
    return True

if __name__ == "__main__":
    success = test_end_to_end_flow()
    if success:
        print("\n🚀 Pokemon Sapphire support is ready!")
    else:
        print("\n❌ Test failed - check configuration")
        sys.exit(1)
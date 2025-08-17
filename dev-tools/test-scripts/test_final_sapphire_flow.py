#!/usr/bin/env python3
"""
Final test of the complete Pokemon Sapphire detection and configuration flow
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_gba_player.settings')
sys.path.append('/Users/chengwan/Projects/pokemonAI/LLM-Pokemon-Red/ai_gba_player')
django.setup()

from dashboard.models import Configuration
from dashboard.game_detector import get_game_detector
from dashboard.ai_game_service import AIGameService

def test_complete_sapphire_flow():
    print("🎮 Final Pokemon Sapphire Detection Flow Test\n")
    
    # Step 1: Verify database configuration
    print("=== Step 1: Database Configuration ===")
    config = Configuration.get_config()
    print(f"✅ ROM Path: {config.rom_path}")
    print(f"✅ ROM Display Name: {config.rom_display_name}")
    print(f"✅ Active Game: {config.game}")
    print(f"✅ Detected Game: {config.detected_game}")
    print(f"✅ Detection Source: {config.detection_source}")
    
    # Step 2: Test AI Service Configuration Loading
    print("\n=== Step 2: AI Service Config Loading ===")
    service = AIGameService()
    config_dict = config.to_dict()
    
    rom_path = config_dict.get('rom_path', '')
    rom_display_name = config_dict.get('rom_display_name', '')
    
    print(f"✅ AI Service sees ROM path: '{rom_path}'")
    print(f"✅ AI Service sees ROM name: '{rom_display_name}'")
    
    # Step 3: Test Game Detection Logic
    print("\n=== Step 3: Game Detection Logic ===")
    detector = service.game_detector
    
    # Test individual detection methods
    name_detection = detector.detect_game_from_rom_name(rom_display_name)
    path_detection = detector.detect_game_from_path(rom_path)
    
    print(f"✅ Name detection: {name_detection}")
    print(f"✅ Path detection: {path_detection}")
    
    # Test final detection with precedence
    detected_game_id, detection_source = detector.get_current_game(
        rom_name=rom_display_name,
        rom_path=rom_path
    )
    
    print(f"✅ Final detection: {detected_game_id} (source: {detection_source})")
    
    # Step 4: Test Game Configuration Generation
    print("\n=== Step 4: Game Configuration Generation ===")
    game_config = detector.get_game_config(detected_game_id)
    
    if game_config:
        print(f"✅ Game Name: {game_config.name}")
        print(f"✅ Platform: {game_config.platform}")
        print(f"✅ Memory Type: {game_config.memory_type}")
        print(f"✅ Direction Encoding: {game_config.direction_encoding}")
        print(f"✅ Fallback Address Sets: {len(game_config.fallback_addresses) if game_config.fallback_addresses else 0}")
    else:
        print("❌ No game configuration found")
        return False
    
    # Step 5: Test Lua Configuration Formatting
    print("\n=== Step 5: Lua Configuration Formatting ===")
    lua_config = detector.format_game_config_for_lua(detected_game_id)
    
    if lua_config:
        print(f"✅ Lua config generated: {len(lua_config)} characters")
        
        # Test parsing (simulate what Lua would do)
        expected_content = [
            'id="pokemon_sapphire"',
            'name="Pokémon Sapphire"',
            'platform="Game Boy Advance"',
            'memoryType="dynamic"',
            '[1]="DOWN"',  # GBA direction encoding
            'fallbackAddresses={'  # Has fallback addresses
        ]
        
        missing_content = []
        for content in expected_content:
            if content not in lua_config:
                missing_content.append(content)
        
        if missing_content:
            print(f"❌ Missing content: {missing_content}")
            return False
        else:
            print("✅ All expected content present in Lua config")
    else:
        print("❌ Failed to generate Lua configuration")
        return False
    
    # Step 6: Test Message Formatting (for socket transmission)
    print("\n=== Step 6: Socket Message Formatting ===")
    
    # Simulate the message that would be sent to Lua
    config_message = f"game_config||{lua_config}"
    print(f"✅ Socket message length: {len(config_message)} characters")
    
    # Check message doesn't have problematic characters
    if '\n' in lua_config:
        print("⚠️  Warning: Lua config contains newlines (may cause parsing issues)")
    else:
        print("✅ Lua config is single-line (good for socket transmission)")
    
    # Step 7: Verify Against Known Issues
    print("\n=== Step 7: Issue Prevention Checks ===")
    
    checks = {
        "Not Pokemon Red": detected_game_id != "pokemon_red",
        "Correct Game ID": detected_game_id == "pokemon_sapphire", 
        "GBA Platform": game_config.platform == "Game Boy Advance",
        "Dynamic Memory": game_config.memory_type == "dynamic",
        "Has Fallbacks": game_config.fallback_addresses and len(game_config.fallback_addresses) > 0,
        "Config Not Empty": lua_config and len(lua_config) > 100,
        "No Concatenation Risk": "request_screenshot" not in lua_config
    }
    
    all_passed = True
    for check_name, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"{status} {check_name}: {passed}")
        if not passed:
            all_passed = False
    
    print(f"\n🎯 Final Result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    if all_passed:
        print("\n🚀 Pokemon Sapphire support is fully working!")
        print("\nWhat you should see when running the system:")
        print("1. mGBA Lua debug: 'Game configured: Pokémon Sapphire (Game Boy Advance)'")
        print("2. AI Service log: '🎮 Game detected: Pokémon Sapphire'")
        print("3. Dynamic memory discovery with 3 fallback address sets")
        print("4. GBA-specific direction encoding (1=DOWN, 2=UP, etc.)")
    
    return all_passed

if __name__ == "__main__":
    success = test_complete_sapphire_flow()
    if not success:
        print("\n❌ Test failed - check the output above for issues")
        sys.exit(1)
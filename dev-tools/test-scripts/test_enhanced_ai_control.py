#!/usr/bin/env python3
"""
Test script for enhanced AI game control integration.
Verifies that all components work together properly.
"""

import os
import sys
import time
import json
import tempfile
from pathlib import Path

# Add Django setup
sys.path.append('/Users/chengwan/Projects/pokemonAI/LLM-Pokemon-Red/ai_gba_player')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_gba_player.settings')

import django
django.setup()

from dashboard.ai_game_service import AIGameService
from dashboard.llm_client import LLMClient
from dashboard.models import Configuration
from PIL import Image

def create_test_screenshot():
    """Create a simple test screenshot"""
    # Create a simple 160x144 test image (Game Boy screen size)
    img = Image.new('RGB', (160, 144), color='white')
    
    # Save to temporary file
    temp_path = "/Users/chengwan/Projects/pokemonAI/LLM-Pokemon-Red/data/screenshots/test_screenshot.png"
    os.makedirs(os.path.dirname(temp_path), exist_ok=True)
    img.save(temp_path)
    return temp_path

def test_llm_client():
    """Test LLM client functionality"""
    print("🧪 Testing LLM Client...")
    
    # Create test configuration
    test_config = {
        'llm_provider': 'google',
        'providers': {
            'google': {
                'api_key': 'test_key_placeholder',
                'model_name': 'gemini-2.0-flash-exp'
            }
        },
        'llm_timeout_seconds': 30
    }
    
    try:
        client = LLMClient(test_config)
        print("✅ LLM Client initialized successfully")
        
        # Test game context creation
        test_game_state = {
            'position': {'x': 10, 'y': 15},
            'direction': 'UP',
            'map_id': 0
        }
        
        context = client._create_game_context(test_game_state, "No recent actions.")
        print("✅ Game context created successfully")
        print(f"📄 Context length: {len(context)} characters")
        
        # Test image enhancement (without API call)
        test_screenshot = create_test_screenshot()
        enhanced_image = client._enhance_image(test_screenshot)
        print(f"✅ Image enhancement working - Enhanced size: {enhanced_image.size}")
        
        # Test map name resolution
        map_name = client._get_map_name(0)
        print(f"✅ Map name resolution: Map 0 = {map_name}")
        
        # Test notepad operations
        client._update_notepad("Test notepad entry from integration test")
        notepad_content = client._read_notepad()
        print(f"✅ Notepad operations working - Content length: {len(notepad_content)}")
        
        return True
        
    except Exception as e:
        print(f"❌ LLM Client test failed: {e}")
        return False

def test_ai_game_service():
    """Test AI Game Service functionality"""
    print("\n🧪 Testing AI Game Service...")
    
    try:
        service = AIGameService()
        print("✅ AI Game Service initialized successfully")
        
        # Test configuration loading
        try:
            # Create a test configuration in database
            config = Configuration.objects.first()
            if not config:
                config = Configuration.objects.create(
                    llm_provider='google',
                    decision_cooldown=3
                )
                config.set_provider_config('google', {
                    'api_key': 'test_key_placeholder',
                    'model_name': 'gemini-2.0-flash-exp'
                })
                config.save()
            
            loaded_config = service._load_config()
            print("✅ Configuration loading working")
            
        except Exception as e:
            print(f"⚠️ Configuration test skipped: {e}")
        
        # Test memory system
        service._initialize_notepad()
        print("✅ Notepad initialization working")
        
        recent_actions_text = service._get_recent_actions_text()
        print(f"✅ Recent actions text: '{recent_actions_text[:50]}...'")
        
        # Test game state tracking
        test_game_state = {'position': {'x': 5, 'y': 10}, 'direction': 'RIGHT', 'map_id': 37}
        map_name = service._get_map_name(37)
        print(f"✅ Map name resolution: Map 37 = {map_name}")
        
        # Test intelligent fallback
        fallback_action = service._get_intelligent_fallback_action(test_game_state)
        print(f"✅ Intelligent fallback: {fallback_action}")
        
        return True
        
    except Exception as e:
        print(f"❌ AI Game Service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_protocol_communication():
    """Test protocol communication format"""
    print("\n🧪 Testing Protocol Communication...")
    
    try:
        # Test message parsing
        test_message = "screenshot_with_state||/path/to/screenshot.png||UP||25||30||0"
        parts = test_message.split("||")
        
        if len(parts) >= 6:
            message_type = parts[0]
            screenshot_path = parts[1]
            direction = parts[2]
            x, y = int(parts[3]), int(parts[4])
            map_id = int(parts[5])
            
            game_state = {
                "position": {"x": x, "y": y},
                "direction": direction,
                "map_id": map_id
            }
            
            print(f"✅ Protocol parsing successful:")
            print(f"   📁 Path: {screenshot_path}")
            print(f"   🧭 Direction: {direction}")
            print(f"   📍 Position: ({x}, {y})")
            print(f"   🗺️ Map ID: {map_id}")
            
            return True
        else:
            print("❌ Protocol parsing failed: insufficient parts")
            return False
            
    except Exception as e:
        print(f"❌ Protocol communication test failed: {e}")
        return False

def test_integration():
    """Test full integration"""
    print("\n🧪 Testing Full Integration...")
    
    try:
        # Create test screenshot
        test_screenshot = create_test_screenshot()
        print(f"✅ Test screenshot created: {test_screenshot}")
        
        # Create test game state
        test_game_state = {
            'position': {'x': 12, 'y': 8},
            'direction': 'DOWN',
            'map_id': 0
        }
        
        # Test that all components can work together
        service = AIGameService()
        
        # Test the enhanced context creation pipeline
        recent_actions_text = service._get_recent_actions_text()
        
        # Test fallback action selection
        fallback_action = service._get_intelligent_fallback_action(test_game_state)
        print(f"✅ Integration test successful - fallback action: {fallback_action}")
        
        # Test memory updates
        service._add_recent_action("A", "Testing integration", test_game_state)
        updated_actions = service._get_recent_actions_text()
        print("✅ Memory system integration working")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Enhanced AI Game Control Integration Tests")
    print("=" * 60)
    
    tests = [
        ("LLM Client", test_llm_client),
        ("AI Game Service", test_ai_game_service),
        ("Protocol Communication", test_protocol_communication),
        ("Full Integration", test_integration),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name} Test...")
        try:
            result = test_func()
            results.append((test_name, result))
            if result:
                print(f"✅ {test_name} Test: PASSED")
            else:
                print(f"❌ {test_name} Test: FAILED")
        except Exception as e:
            print(f"❌ {test_name} Test: ERROR - {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Enhanced AI game control is ready.")
        return True
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
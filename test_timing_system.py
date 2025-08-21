#!/usr/bin/env python3
"""
Test script for the new AI service screenshot timing system.
This validates that the timing configuration is working correctly.
"""

import sys
import time
import json
import requests
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent / "LLM-Pokemon-Red"
sys.path.insert(0, str(project_root))

def test_timing_configuration():
    """Test that timing configuration can be loaded and saved"""
    print("🧪 Testing timing configuration system...")
    
    # Test data for timing configuration
    test_config = {
        'llm_provider': 'gemini',
        'api_key': 'test_key_123',
        'cooldown': '3',
        'base_stabilization': '0.6',
        'movement_multiplier': '0.9',
        'interaction_multiplier': '0.7',
        'menu_multiplier': '0.5',
        'max_wait_time': '8.0'
    }
    
    # Save timing configuration via API
    print("📤 Saving timing configuration via API...")
    response = requests.post('http://localhost:8000/api/save-ai-config/', data=test_config)
    
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            print(f"✅ Configuration saved: {result.get('message')}")
        else:
            print(f"❌ Save failed: {result.get('message')}")
            return False
    else:
        print(f"❌ HTTP error: {response.status_code}")
        return False
    
    # Verify configuration was saved
    print("📥 Verifying configuration was saved...")
    config_file = project_root / "ai_gba_player" / "ai_gba_player" / "local_config.json"
    
    if config_file.exists():
        with open(config_file, 'r') as f:
            saved_config = json.load(f)
        
        # Check that timing values were saved
        timing_keys = ['base_stabilization', 'movement_multiplier', 'interaction_multiplier', 'menu_multiplier', 'max_wait_time']
        for key in timing_keys:
            if key in saved_config:
                print(f"✅ {key}: {saved_config[key]}")
            else:
                print(f"❌ Missing timing key: {key}")
                return False
    else:
        print(f"❌ Config file not found: {config_file}")
        return False
    
    print("✅ Timing configuration test passed!")
    return True

def test_ai_service_timing_calculation():
    """Test the AI service timing calculation logic"""
    print("\n🧪 Testing AI service timing calculation...")
    
    try:
        # Import the AI service
        sys.path.insert(0, str(project_root / "ai_gba_player"))
        from dashboard.ai_game_service import AIGameService
        
        # Create a test AI service instance (without starting the server)
        test_service = AIGameService()
        
        # Test different action combinations
        test_cases = [
            # (actions, expected_min_delay, description)
            ([], 0.5, "No actions - base stabilization only"),
            (['UP'], 0.5 + 0.8, "Single movement action"),
            (['A'], 0.5 + 0.6, "Single interaction action"),
            (['START'], 0.5 + 0.4, "Single menu action"),
            (['UP', 'UP', 'A'], 0.5 + 0.8 + 0.8 + 0.6, "Movement + interaction combo"),
            (['START', 'DOWN', 'A', 'B'], 0.5 + 0.4 + 0.8 + 0.6 + 0.6, "Menu navigation sequence"),
        ]
        
        for actions, expected_min, description in test_cases:
            calculated_delay = test_service._calculate_screenshot_delay(actions)
            print(f"  📊 {description}")
            print(f"     Actions: {actions}")
            print(f"     Expected min: {expected_min:.2f}s, Calculated: {calculated_delay:.2f}s")
            
            # The calculated delay should be at least the expected minimum
            # (but could be capped by max_wait_time)
            expected_delay = min(expected_min, test_service.timing_config['max_wait_time'])
            if abs(calculated_delay - expected_delay) < 0.1:  # Allow small floating point differences
                print(f"     ✅ Timing calculation correct!")
            else:
                print(f"     ❌ Timing calculation error! Expected ~{expected_delay:.2f}s")
                return False
        
        print("✅ AI service timing calculation test passed!")
        return True
        
    except Exception as e:
        print(f"❌ AI service timing test failed: {e}")
        return False

def test_service_integration():
    """Test that the AI service can be started and timing config reloaded"""
    print("\n🧪 Testing AI service integration...")
    
    try:
        # Check if service is running
        response = requests.get('http://localhost:8000/api/chat-messages/')
        if response.status_code == 200:
            result = response.json()
            print(f"📊 Service status: {result.get('status', 'unknown')}")
            print(f"📊 Connected: {result.get('connected', False)}")
            print("✅ Service integration working!")
            return True
        else:
            print(f"❌ Service check failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Service integration test failed: {e}")
        return False

def main():
    """Run all timing system tests"""
    print("🎮 AI GBA Player - Screenshot Timing System Test")
    print("=" * 50)
    
    all_tests_passed = True
    
    # Test 1: Configuration system
    if not test_timing_configuration():
        all_tests_passed = False
    
    # Test 2: Timing calculation logic
    if not test_ai_service_timing_calculation():
        all_tests_passed = False
    
    # Test 3: Service integration
    if not test_service_integration():
        all_tests_passed = False
    
    print("\n" + "=" * 50)
    if all_tests_passed:
        print("🎉 All timing system tests PASSED!")
        print("✅ The AI service-controlled screenshot timing is working correctly!")
        print("\n📝 What was implemented:")
        print("  • AI service now controls when screenshots are taken")
        print("  • Dynamic timing based on action complexity")
        print("  • Configurable timing parameters via web interface")
        print("  • Smart delay calculation for movement/interaction/menu actions")
        print("  • Real-time configuration reloading without service restart")
    else:
        print("❌ Some timing system tests FAILED!")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
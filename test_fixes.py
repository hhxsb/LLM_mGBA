#!/usr/bin/env python3
"""
Test script to validate the fixes for chat messages and protocol parsing.
"""

import os
import sys

# Add Django setup
sys.path.append('/Users/chengwan/Projects/pokemonAI/LLM-Pokemon-Red/ai_gba_player')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_gba_player.settings')

import django
django.setup()

from dashboard.ai_game_service import AIGameService

def test_protocol_parsing_fix():
    """Test the protocol parsing fix for direction strings"""
    print("🧪 Testing Protocol Parsing Fix...")
    
    service = AIGameService()
    
    # Test cases for direction parsing
    test_cases = [
        {
            "message": "screenshot_with_state||/path/test.png||UP||25||30||0",
            "expected": {"direction": "UP", "x": 25, "y": 30, "map_id": 0}
        },
        {
            "message": "screenshot_with_state||/path/test.png||UNKNOWN (48)||15||20||37",
            "expected": {"direction": "UNKNOWN", "x": 15, "y": 20, "map_id": 37}
        },
        {
            "message": "screenshot_with_state||/path/test.png||DOWN||5||10||40",
            "expected": {"direction": "DOWN", "x": 5, "y": 10, "map_id": 40}
        },
        {
            "message": "screenshot_with_state||/path/test.png||weird_value||100||200||1",
            "expected": {"direction": "UNKNOWN", "x": 100, "y": 200, "map_id": 1}
        }
    ]
    
    results = []
    for i, test_case in enumerate(test_cases, 1):
        try:
            print(f"\n  Test {i}: {test_case['message']}")
            
            # Parse the message manually (simulating _handle_screenshot_data logic)
            parts = test_case["message"].split("||")
            if len(parts) >= 6:
                direction = parts[2]
                x = int(parts[3])
                y = int(parts[4])
                map_id = int(parts[5])
                
                # Test direction normalization
                normalized_direction = service._normalize_direction(direction)
                
                actual = {
                    "direction": normalized_direction,
                    "x": x,
                    "y": y,
                    "map_id": map_id
                }
                
                expected = test_case["expected"]
                match = all(actual[k] == expected[k] for k in expected.keys())
                
                if match:
                    print(f"    ✅ PASS: {actual}")
                    results.append(True)
                else:
                    print(f"    ❌ FAIL: Expected {expected}, got {actual}")
                    results.append(False)
            else:
                print(f"    ❌ FAIL: Invalid message format")
                results.append(False)
                
        except Exception as e:
            print(f"    ❌ ERROR: {e}")
            results.append(False)
    
    passed = sum(results)
    total = len(results)
    print(f"\n📊 Protocol Parsing: {passed}/{total} tests passed")
    return passed == total

def test_chat_message_buffer():
    """Test the chat message buffer improvements"""
    print("\n🧪 Testing Chat Message Buffer...")
    
    service = AIGameService()
    
    # Test message counter and buffer management
    print(f"  Initial state: {len(service.chat_messages)} messages, counter: {service.message_counter}")
    
    # Send multiple messages to test buffer
    test_messages = [
        "Test message 1",
        "Test message 2", 
        "Test message 3",
        "Test message with special chars: UNKNOWN (48)",
        "Test message 5"
    ]
    
    for i, msg in enumerate(test_messages, 1):
        service._send_chat_message("system", msg)
        print(f"  After message {i}: {len(service.chat_messages)} messages, counter: {service.message_counter}")
    
    # Verify message IDs are sequential
    message_ids = [msg.get('id', 0) for msg in service.chat_messages]
    sequential = all(message_ids[i] == message_ids[i-1] + 1 for i in range(1, len(message_ids)))
    
    if sequential:
        print("  ✅ Message IDs are sequential")
    else:
        print(f"  ❌ Message IDs not sequential: {message_ids}")
    
    # Test buffer size increase
    max_size = service.max_messages
    if max_size >= 500:
        print(f"  ✅ Buffer size increased to {max_size}")
    else:
        print(f"  ❌ Buffer size not increased: {max_size}")
    
    # Test message structure
    if service.chat_messages:
        last_msg = service.chat_messages[-1]
        required_fields = ['type', 'content', 'timestamp', 'id']
        has_all_fields = all(field in last_msg for field in required_fields)
        
        if has_all_fields:
            print("  ✅ Messages have required fields")
        else:
            print(f"  ❌ Missing fields in message: {last_msg}")
            return False
    
    return sequential and max_size >= 500

def test_direction_normalization():
    """Test direction normalization function"""
    print("\n🧪 Testing Direction Normalization...")
    
    service = AIGameService()
    
    test_cases = [
        ("UP", "UP"),
        ("DOWN", "DOWN"),
        ("LEFT", "LEFT"),
        ("RIGHT", "RIGHT"),
        ("UNKNOWN (48)", "UNKNOWN"),
        ("UNKNOWN (123)", "UNKNOWN"),
        ("unknown", "UNKNOWN"),
        ("invalid_direction", "UNKNOWN"),
        ("", "UNKNOWN"),
        (None, "UNKNOWN")
    ]
    
    results = []
    for input_dir, expected in test_cases:
        try:
            actual = service._normalize_direction(input_dir)
            if actual == expected:
                print(f"  ✅ '{input_dir}' -> '{actual}'")
                results.append(True)
            else:
                print(f"  ❌ '{input_dir}' -> '{actual}' (expected '{expected}')")
                results.append(False)
        except Exception as e:
            print(f"  ❌ Error with '{input_dir}': {e}")
            results.append(False)
    
    passed = sum(results)
    total = len(results)
    print(f"📊 Direction Normalization: {passed}/{total} tests passed")
    return passed == total

def test_fallback_action_with_unknown_direction():
    """Test fallback action handling with unknown directions"""
    print("\n🧪 Testing Fallback Actions with Unknown Directions...")
    
    service = AIGameService()
    
    test_states = [
        {
            "game_state": {"position": {"x": 10, "y": 15}, "direction": "UNKNOWN (48)", "map_id": 0},
            "description": "Pallet Town with unknown direction"
        },
        {
            "game_state": {"position": {"x": 5, "y": 10}, "direction": "UNKNOWN", "map_id": 37},
            "description": "Player's house with unknown direction"
        },
        {
            "game_state": {"position": {"x": 8, "y": 12}, "direction": "UP", "map_id": 40},
            "description": "Oak's lab with known direction"
        }
    ]
    
    results = []
    for test in test_states:
        try:
            action = service._get_intelligent_fallback_action(test["game_state"])
            valid_actions = ["A", "B", "UP", "DOWN", "LEFT", "RIGHT", "START", "SELECT"]
            
            if action in valid_actions:
                print(f"  ✅ {test['description']}: {action}")
                results.append(True)
            else:
                print(f"  ❌ {test['description']}: Invalid action '{action}'")
                results.append(False)
        except Exception as e:
            print(f"  ❌ Error with {test['description']}: {e}")
            results.append(False)
    
    passed = sum(results)
    total = len(results)
    print(f"📊 Fallback Actions: {passed}/{total} tests passed")
    return passed == total

def main():
    """Run all fix validation tests"""
    print("🚀 Running Fix Validation Tests")
    print("=" * 50)
    
    tests = [
        ("Protocol Parsing Fix", test_protocol_parsing_fix),
        ("Chat Message Buffer", test_chat_message_buffer),
        ("Direction Normalization", test_direction_normalization),
        ("Fallback Actions", test_fallback_action_with_unknown_direction)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} Test: ERROR - {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 Fix Validation Results:")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All fixes validated! Issues should be resolved.")
        print("\n💡 Key Improvements:")
        print("  • Fixed 'UNKNOWN (48)' parsing errors")
        print("  • Increased message buffer from 100 to 500")
        print("  • Added message IDs for better tracking")
        print("  • Improved direction normalization")
        print("  • Enhanced error handling and fallbacks")
        return True
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
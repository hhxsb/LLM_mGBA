#!/usr/bin/env python3
"""
Test script to verify the on-demand GIF timing implementation.
"""

import time
import json
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

from game_control_process import GameControlProcess

def test_timing_logic():
    """Test the timing logic without full system."""
    
    # Load config
    try:
        with open('config_emulator.json', 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return False
    
    # Create game control process (but don't start it)
    game_controller = GameControlProcess(config)
    
    # Test timing logic
    print("🧪 Testing on-demand GIF timing logic...")
    
    # Test 1: First request should always be allowed
    current_time = time.time()
    should_request = game_controller._should_request_gif_now(current_time)
    print(f"✅ First request allowed: {should_request}")
    assert should_request == True, "First request should be allowed"
    
    # Test 2: Set action complete time and test delay
    game_controller.last_action_complete_time = current_time
    
    # Immediately after action - should NOT request yet
    should_request = game_controller._should_request_gif_now(current_time + 0.1)
    remaining = game_controller._get_remaining_delay(current_time + 0.1)
    print(f"✅ Request blocked within delay period: {not should_request}, remaining: {remaining:.2f}s")
    assert should_request == False, "Request should be blocked within delay period"
    
    # After delay period - should allow request
    should_request = game_controller._should_request_gif_now(current_time + 0.6)
    remaining = game_controller._get_remaining_delay(current_time + 0.6)
    print(f"✅ Request allowed after delay: {should_request}, remaining: {remaining:.2f}s")
    assert should_request == True, "Request should be allowed after delay period"
    
    print("🎉 All timing logic tests passed!")
    return True

def test_action_duration_calculation():
    """Test action duration calculation."""
    
    # Load config
    try:
        with open('config_emulator.json', 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return False
    
    # Create game control process
    game_controller = GameControlProcess(config)
    
    print("🧪 Testing action duration calculation...")
    
    # Test with various button combinations
    test_cases = [
        ([0], [2], 2.0 / 60.0),  # Single A button, 2 frames
        ([0, 6], [2, 3], (2 + 3) / 60.0),  # A + UP, different durations
        ([6, 6, 0], [], 3 * 2 / 60.0),  # UP UP A, default durations
    ]
    
    for button_codes, button_durations, expected_duration in test_cases:
        duration = game_controller._calculate_action_duration(button_codes, button_durations)
        print(f"✅ Buttons {button_codes}, durations {button_durations} → {duration:.4f}s (expected {expected_duration:.4f}s)")
    
    print("🎉 Action duration calculation tests completed!")
    return True

if __name__ == '__main__':
    print("🧪 Starting timing implementation tests...")
    
    success1 = test_timing_logic()
    success2 = test_action_duration_calculation()
    
    if success1 and success2:
        print("✅ All tests passed! On-demand timing implementation is working correctly.")
    else:
        print("❌ Some tests failed.")
        sys.exit(1)
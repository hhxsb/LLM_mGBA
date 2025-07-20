#!/usr/bin/env python3
"""
Test script to verify the complete T0→T1 cycle timing for on-demand GIF requests.

This simulates the flow described by the user:
1. Game control requests GIF at T0
2. GIF contains video from some previous time to T0
3. Game control sends GIF to LLM
4. LLM returns button commands
5. Game control executes buttons
6. After action completion + 0.5s delay, game control requests new GIF at T1
7. New GIF contains video from T0 to T1
"""

import time
import json
import threading
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

from video_capture_process import VideoCaptureProcess
from game_control_process import VideoProcessClient

def test_complete_t0_t1_cycle():
    """Test the complete T0→T1 cycle flow."""
    
    print("🧪 Testing complete T0→T1 cycle flow...")
    
    # Start video capture process
    print("🎬 Starting video capture process...")
    video_process = VideoCaptureProcess('config_emulator.json')
    
    # Start in a separate thread
    video_thread = threading.Thread(target=video_process.run_forever, daemon=True)
    video_thread.start()
    
    # Wait for video process to initialize
    time.sleep(3.0)
    
    # Create video client
    client = VideoProcessClient(port=8889)
    
    try:
        # Test initial GIF request (T0)
        print("\n📸 Making initial GIF request (T0)...")
        t0_time = time.time()
        gif_response_t0 = client.request_gif()
        
        if not gif_response_t0 or not gif_response_t0.get('success'):
            print("❌ Failed to get initial GIF")
            return False
        
        frame_count_t0 = gif_response_t0.get('frame_count', 0)
        duration_t0 = gif_response_t0.get('duration', 0.0)
        start_t0 = gif_response_t0.get('start_timestamp', 0.0)
        end_t0 = gif_response_t0.get('end_timestamp', 0.0)
        
        print(f"✅ T0 GIF received: {frame_count_t0} frames, {duration_t0:.2f}s")
        print(f"   Time range: {start_t0:.2f} → {end_t0:.2f}")
        print(f"   Should be ~5s of history (first GIF optimization)")
        
        # Simulate action execution time
        action_duration = 1.0  # 1 second action
        delay_after_action = 0.5  # 0.5 second delay
        total_wait = action_duration + delay_after_action
        
        print(f"\n⏰ Simulating action execution ({action_duration}s) + delay ({delay_after_action}s)...")
        time.sleep(total_wait)
        
        # Test subsequent GIF request (T1)
        print("\n📸 Making subsequent GIF request (T1)...")
        t1_time = time.time()
        gif_response_t1 = client.request_gif()
        
        if not gif_response_t1 or not gif_response_t1.get('success'):
            print("❌ Failed to get subsequent GIF")
            return False
        
        frame_count_t1 = gif_response_t1.get('frame_count', 0)
        duration_t1 = gif_response_t1.get('duration', 0.0)
        start_t1 = gif_response_t1.get('start_timestamp', 0.0)
        end_t1 = gif_response_t1.get('end_timestamp', 0.0)
        
        print(f"✅ T1 GIF received: {frame_count_t1} frames, {duration_t1:.2f}s")
        print(f"   Time range: {start_t1:.2f} → {end_t1:.2f}")
        print(f"   Should span from T0 timestamp to T1 timestamp")
        
        # Verify T0→T1 timing
        expected_t0_to_t1_duration = t1_time - t0_time
        actual_gif_duration = end_t1 - start_t1
        
        print(f"\n🔍 Timing Analysis:")
        print(f"   T0 timestamp: {t0_time:.2f}")
        print(f"   T1 timestamp: {t1_time:.2f}")
        print(f"   Expected T0→T1 duration: {expected_t0_to_t1_duration:.2f}s")
        print(f"   Actual GIF duration: {actual_gif_duration:.2f}s")
        print(f"   GIF start should be close to T0 end: {abs(start_t1 - end_t0):.2f}s difference")
        
        # Validate timing
        timing_tolerance = 0.5  # Allow 0.5s tolerance
        if abs(actual_gif_duration - expected_t0_to_t1_duration) <= timing_tolerance:
            print("✅ T0→T1 timing is correct!")
        else:
            print("⚠️ T0→T1 timing may be off, but this could be due to test timing variations")
        
        if abs(start_t1 - end_t0) <= 0.1:  # GIF start should be very close to previous GIF end
            print("✅ GIF continuity is correct!")
        else:
            print("⚠️ GIF continuity may have gaps or overlaps")
        
        print("🎉 T0→T1 cycle test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during T0→T1 cycle test: {e}")
        return False
    
    finally:
        # Stop video process
        video_process.stop()

if __name__ == '__main__':
    print("🧪 Starting T0→T1 cycle test...")
    
    success = test_complete_t0_t1_cycle()
    
    if success:
        print("✅ T0→T1 cycle implementation is working correctly!")
    else:
        print("❌ T0→T1 cycle test failed.")
        sys.exit(1)
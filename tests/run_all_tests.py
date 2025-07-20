#!/usr/bin/env python3
"""
Run all knowledge system feature tests.
"""

import subprocess
import sys
import os

def run_test(test_file):
    """Run a single test file and return success status."""
    print(f"\n{'='*60}")
    print(f"🧪 Running {test_file}")
    print('='*60)
    
    try:
        result = subprocess.run([sys.executable, test_file], 
                              capture_output=False, 
                              cwd=os.path.dirname(os.path.abspath(__file__)))
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error running {test_file}: {e}")
        return False

def main():
    """Run all tests in the correct order."""
    print("🚀 Starting comprehensive knowledge system test suite...")
    
    # List of tests in logical order
    tests = [
        "test_conversation_tracking.py",
        "test_character_tracking.py", 
        "test_context_memory.py",
        "test_prompt_formatting.py",
        "test_dialogue_recording.py",
        "test_conversation_flow.py",
        "test_context_prioritization.py",
        "test_tutorial_progress.py",
    ]
    
    passed_tests = []
    failed_tests = []
    
    for test in tests:
        if os.path.exists(test):
            success = run_test(test)
            if success:
                passed_tests.append(test)
                print(f"✅ {test} PASSED")
            else:
                failed_tests.append(test)
                print(f"❌ {test} FAILED")
        else:
            print(f"⚠️ {test} not found, skipping...")
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print('='*60)
    print(f"✅ Passed: {len(passed_tests)}")
    print(f"❌ Failed: {len(failed_tests)}")
    print(f"📈 Success Rate: {len(passed_tests)}/{len(passed_tests) + len(failed_tests)} ({(len(passed_tests)/(len(passed_tests) + len(failed_tests))*100):.1f}%)")
    
    if passed_tests:
        print(f"\n✅ Passed Tests:")
        for test in passed_tests:
            print(f"   - {test}")
    
    if failed_tests:
        print(f"\n❌ Failed Tests:")
        for test in failed_tests:
            print(f"   - {test}")
        print(f"\n🔧 Check individual test output for debugging information.")
    else:
        print(f"\n🎉 All tests passed! Knowledge system is working correctly.")
    
    return len(failed_tests) == 0

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
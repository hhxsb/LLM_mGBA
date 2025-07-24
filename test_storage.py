#!/usr/bin/env python3
"""
Test script for SQLite storage system.
"""

import asyncio
import json
import os
import sys
import time
from PIL import Image, ImageDraw

# Add project root to path
sys.path.append(os.path.dirname(__file__))

from core.storage_service import StorageService, prepare_decision_data, prepare_action_data
from core.database_manager import DatabaseManager
from core.logging_config import configure_logging, get_logger


async def test_storage_system():
    """Test the storage system components."""
    
    # Configure logging
    configure_logging(debug=True, process_name="storage_test")
    logger = get_logger("storage_test")
    
    logger.info("🧪 Starting storage system tests...")
    
    # Load test configuration
    config = {
        "game": "pokemon_red",
        "player_name": "TEST_GEMINI",
        "initial_objective": "Test storage system",
        "storage": {
            "enabled": True,
            "database_path": "data/test_pokemon_ai.db",
            "wal_mode": True,
            "gif_storage_threshold_mb": 1,
            "compression_level": 6
        }
    }
    
    try:
        # Test 1: Database initialization
        logger.info("📊 Test 1: Database initialization")
        storage_service = StorageService(config)
        await storage_service.initialize()
        logger.info("✅ Database initialized successfully")
        
        # Test 2: Session creation
        logger.info("🎮 Test 2: Session creation")
        session_id = await storage_service.start_session("pokemon_red", "TEST_GEMINI")
        logger.info(f"Session created: {session_id}")
        logger.info("✅ Session creation successful")
        
        # Test 3: Store AI decision and action
        logger.info("💭 Test 3: Store AI decision and action")
        
        # Prepare test decision data
        decision_data = prepare_decision_data(
            llm_response_text="I can see the Pokemon Red start screen. I should press A to continue.",
            llm_reasoning="The game is at the start screen, pressing A will advance the game.",
            llm_raw_response="Raw LLM response with additional details...",
            processing_time_ms=1500.0,
            game_state={
                "map_id": 1,
                "player_x": 5,
                "player_y": 4,
                "facing_direction": 0,
                "map_name": "Player's House"
            },
            conversation_context={"current_npc": None, "conversation_phase": "none"},
            memory_context={"recent_actions": ["started_game"]},
            tutorial_step="game_start"
        )
        
        # Prepare test action data
        action_data = prepare_action_data(
            button_codes=[0],  # A button
            button_names=["A"],
            button_durations=[2],
            execution_time_ms=50.0,
            success=True
        )
        
        # Store the AI cycle
        decision_id, action_id, gif_id = await storage_service.record_ai_cycle(decision_data, action_data)
        logger.info(f"Stored: decision={decision_id[:8]}, action={action_id[:8]}")
        logger.info("✅ AI cycle storage successful")
        
        # Test 4: Store test GIF
        logger.info("🎥 Test 4: Store test GIF")
        
        # Create a simple test GIF
        test_image = Image.new('RGB', (160, 144), color='green')
        draw = ImageDraw.Draw(test_image)
        draw.text((10, 10), "Test Frame", fill='white')
        
        gif_id = await storage_service.store_gif_from_pil(
            decision_id=decision_id,
            gif_image=test_image,
            frame_count=1,
            duration=1.0,
            fps=1.0
        )
        logger.info(f"Stored GIF: {gif_id[:8]}")
        logger.info("✅ GIF storage successful")
        
        # Test 5: Retrieve gameplay history
        logger.info("📊 Test 5: Retrieve gameplay history")
        history = await storage_service.get_gameplay_history({'limit': 10})
        logger.info(f"Retrieved {len(history['decisions'])} decisions")
        logger.info(f"Session info: {history['session_info']}")
        logger.info("✅ History retrieval successful")
        
        # Test 6: Storage metrics
        logger.info("📈 Test 6: Storage metrics")
        metrics = await storage_service.get_storage_metrics()
        logger.info(f"Database size: {metrics.get('database_file_size_mb', 0):.2f} MB")
        logger.info(f"Current session: {metrics.get('current_session_id', 'none')}")
        logger.info("✅ Metrics retrieval successful")
        
        # Test 7: Export session data
        logger.info("📤 Test 7: Export session data")
        export_data = await storage_service.export_session_data(session_id)
        logger.info(f"Exported data contains {len(export_data.get('decisions', []))} decisions")
        logger.info("✅ Data export successful")
        
        # Close session
        await storage_service.close_current_session("test_completed")
        logger.info("🏁 Test session closed")
        
        # Summary
        logger.info("🎉 All storage system tests completed successfully!")
        
        # Clean up test database
        test_db_path = config['storage']['database_path']
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
            logger.info(f"🧹 Cleaned up test database: {test_db_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Storage test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_database_manager():
    """Test the database manager directly."""
    
    logger = get_logger("db_test")
    logger.info("🗃️ Testing DatabaseManager directly...")
    
    try:
        # Test database creation and operations
        db_manager = DatabaseManager("data/test_db_manager.db")
        await db_manager.initialize_database()
        
        # Test session creation
        session_id = await db_manager.create_session("pokemon_red", "TEST_USER", "Test objective")
        logger.info(f"Created session: {session_id}")
        
        # Test decision storage
        decision_data = {
            'session_id': session_id,
            'sequence_number': 1,
            'llm_response_text': 'Test response',
            'llm_reasoning': 'Test reasoning',
            'llm_raw_response': 'Raw response',
            'processing_time_ms': 1000.0,
            'game_state': {'test': 'data'},
            'map_name': 'Test Map',
            'player_x': 1,
            'player_y': 2,
            'conversation_context': {},
            'memory_context': {},
            'tutorial_step': 'test_step'
        }
        
        decision_id = await db_manager.store_decision(decision_data)
        logger.info(f"Stored decision: {decision_id}")
        
        # Test action storage
        action_data = {
            'decision_id': decision_id,
            'session_id': session_id,
            'button_codes': [0, 4],
            'button_names': ['A', 'RIGHT'],
            'button_durations': [2, 2],
            'execution_time_ms': 100.0,
            'success': True
        }
        
        action_id = await db_manager.store_action(action_data)
        logger.info(f"Stored action: {action_id}")
        
        # Test retrieval
        recent_decisions = await db_manager.get_recent_decisions(session_id, 5)
        logger.info(f"Retrieved {len(recent_decisions)} recent decisions")
        
        # Test analytics
        analytics = await db_manager.get_session_analytics(session_id)
        logger.info(f"Analytics: {analytics}")
        
        # Close session
        await db_manager.close_session(session_id, "test_completed")
        
        logger.info("✅ DatabaseManager tests completed")
        
        # Clean up
        if os.path.exists("data/test_db_manager.db"):
            os.remove("data/test_db_manager.db")
            logger.info("🧹 Cleaned up test database")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ DatabaseManager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    
    print("🧪 Running SQLite Storage System Tests\n")
    
    # Test 1: Database Manager
    print("=" * 50)
    print("TEST 1: Database Manager")
    print("=" * 50)
    
    db_success = await test_database_manager()
    
    # Test 2: Storage Service
    print("\n" + "=" * 50)
    print("TEST 2: Storage Service")
    print("=" * 50)
    
    storage_success = await test_storage_system()
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    if db_success and storage_success:
        print("🎉 All tests PASSED! Storage system is ready.")
        return 0
    else:
        print("❌ Some tests FAILED. Check the logs above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
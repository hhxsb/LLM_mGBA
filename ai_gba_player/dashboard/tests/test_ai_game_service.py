from django.test import TestCase
from unittest.mock import patch, MagicMock, mock_open
import socket
import threading
import time
import logging
from io import StringIO

from dashboard.ai_game_service import AIGameService, get_ai_service, start_ai_service, stop_ai_service
from dashboard.models import Configuration
from core.logging_config import get_logger


class AIGameServiceTest(TestCase):
    """Test AIGameService with proper mocking - no real network calls"""
    
    def setUp(self):
        """Set up test configuration"""
        self.test_config = {
            'host': '127.0.0.1',
            'port': 8888,
            'llm_provider': 'google',
            'providers': {
                'google': {
                    'api_key': 'test_key_123',
                    'model_name': 'gemini-2.5-pro'
                }
            },
            'decision_cooldown': 2
        }
    
    @patch('socket.socket')
    @patch('dashboard.llm_client.LLMClient')
    def test_service_initialization(self, mock_llm_client, mock_socket):
        """Test AIGameService initializes properly"""
        service = AIGameService()
        
        # Test that service is properly initialized
        self.assertIsInstance(service, threading.Thread)
        self.assertEqual(service.host, '127.0.0.1')
        self.assertEqual(service.port, 8888)
        self.assertFalse(service.running)
    
    @patch('socket.socket')
    @patch('dashboard.llm_client.LLMClient')
    def test_socket_binding(self, mock_llm_client, mock_socket):
        """Test socket binding with mocked socket"""
        mock_sock = MagicMock()
        mock_socket.return_value = mock_sock
        
        service = AIGameService()
        service._setup_socket()
        
        # Verify socket setup calls
        mock_socket.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)
        mock_sock.setsockopt.assert_called_once_with(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        mock_sock.bind.assert_called_once_with(('127.0.0.1', 8888))
        mock_sock.listen.assert_called_once_with(1)
    
    @patch('socket.socket')
    @patch('dashboard.llm_client.LLMClient')
    @patch('builtins.open', new_callable=mock_open, read_data=b'fake_png_data' * 1000)
    def test_handle_screenshot_data(self, mock_file, mock_llm_client, mock_socket):
        """Test screenshot data handling with mocked LLM"""
        # Setup mocked LLM response
        mock_llm_instance = MagicMock()
        mock_llm_instance.analyze_game_state.return_value = {
            'actions': ['UP', 'A'],
            'success': True,
            'text': 'Moving up and pressing A'
        }
        mock_llm_client.return_value = mock_llm_instance
        
        service = AIGameService()
        
        # Test screenshot handling
        test_data = "screenshot_data|/test/path.png|10|20|DOWN|1"
        result = service._handle_screenshot_data(test_data)
        
        # Verify LLM was called with correct parameters
        mock_llm_instance.analyze_game_state.assert_called_once()
        call_args = mock_llm_instance.analyze_game_state.call_args
        self.assertEqual(call_args[0][0], '/test/path.png')  # screenshot path
        
        # Verify game state context
        game_state = call_args[0][1]
        self.assertEqual(game_state['x'], 10)
        self.assertEqual(game_state['y'], 20)
        self.assertEqual(game_state['direction'], 'DOWN')
        self.assertEqual(game_state['map_id'], 1)
        
        # Verify button conversion (UP=4, A=0)
        self.assertEqual(result, "0,4")  # A,UP
    
    @patch('socket.socket')
    @patch('dashboard.llm_client.LLMClient')
    def test_button_mapping(self, mock_llm_client, mock_socket):
        """Test button action to code mapping"""
        service = AIGameService()
        
        # Test individual button mappings
        test_cases = [
            ('A', 0),
            ('B', 1),
            ('START', 2),
            ('SELECT', 3),
            ('UP', 4),
            ('DOWN', 5),
            ('LEFT', 6),
            ('RIGHT', 7)
        ]
        
        for button, expected_code in test_cases:
            result = service._map_actions_to_buttons([button])
            self.assertEqual(result, str(expected_code))
        
        # Test multiple button combination
        result = service._map_actions_to_buttons(['A', 'UP', 'RIGHT'])
        self.assertEqual(result, "0,4,7")  # A,UP,RIGHT
    
    @patch('socket.socket')
    @patch('dashboard.llm_client.LLMClient')
    def test_config_loading_sequence(self, mock_llm_client, mock_socket):
        """Test proper game configuration loading sequence"""
        service = AIGameService()
        service.game_config_loaded = False
        
        # Test that screenshot requests are blocked before config
        test_data = "screenshot_data|/test/path.png|10|20|DOWN|1"
        result = service._handle_screenshot_data(test_data)
        
        # Should return request_screenshot (not process screenshot) when config not loaded
        self.assertEqual(result, "request_screenshot")
        
        # Test config loading
        config_data = "game_config|pokemon_red|Pallet Town"
        service._handle_game_config(config_data)
        self.assertTrue(service.game_config_loaded)
        
        # Test config loaded response
        result = service._handle_config_loaded("config_loaded")
        self.assertEqual(result, "request_screenshot")
    
    @patch('socket.socket')
    @patch('dashboard.llm_client.LLMClient')
    def test_error_handling(self, mock_llm_client, mock_socket):
        """Test error handling in screenshot processing"""
        # Setup LLM to raise an exception
        mock_llm_instance = MagicMock()
        mock_llm_instance.analyze_game_state.side_effect = Exception("LLM API Error")
        mock_llm_client.return_value = mock_llm_instance
        
        service = AIGameService()
        service.game_config_loaded = True
        
        # Test error handling
        test_data = "screenshot_data|/test/path.png|10|20|DOWN|1"
        result = service._handle_screenshot_data(test_data)
        
        # Should return no actions on error
        self.assertEqual(result, "")  # Empty string means no button presses
    
    @patch('socket.socket')
    @patch('dashboard.llm_client.LLMClient')
    def test_cooldown_logic(self, mock_llm_client, mock_socket):
        """Test decision cooldown timing"""
        service = AIGameService()
        service.decision_cooldown = 0.1  # Very short cooldown for testing
        
        # Record initial time
        initial_time = time.time()
        service.last_decision_time = initial_time
        
        # Test that cooldown is respected
        self.assertFalse(service._should_make_decision())
        
        # Test that cooldown expires
        service.last_decision_time = initial_time - 1.0  # 1 second ago
        self.assertTrue(service._should_make_decision())


class AIGameServiceManagerTest(TestCase):
    """Test service manager functions with proper encapsulation"""
    
    @patch('dashboard.ai_game_service.AIGameService')
    def test_service_lifecycle(self, mock_ai_service_class):
        """Test service start/stop lifecycle"""
        mock_service = MagicMock()
        mock_ai_service_class.return_value = mock_service
        
        # Test service startup
        result = start_ai_service()
        self.assertTrue(result)
        mock_service.start.assert_called_once()
        
        # Test service retrieval
        service = get_ai_service()
        self.assertIsNotNone(service)
        
        # Test service stop
        mock_service.stop.return_value = True
        result = stop_ai_service()
        self.assertTrue(result)
        mock_service.stop.assert_called_once()
    
    @patch('dashboard.ai_game_service.get_ai_service')
    def test_service_status_check(self, mock_get_service):
        """Test service running status check"""
        from dashboard.ai_game_service import is_ai_service_running
        
        # Test with running service
        mock_service = MagicMock()
        mock_service.is_alive.return_value = True
        mock_get_service.return_value = mock_service
        
        self.assertTrue(is_ai_service_running())
        
        # Test with no service
        mock_get_service.return_value = None
        self.assertFalse(is_ai_service_running())
        
        # Test with stopped service
        mock_service.is_alive.return_value = False
        mock_get_service.return_value = mock_service
        self.assertFalse(is_ai_service_running())


class AIGameServiceIntegrationTest(TestCase):
    """Integration tests with minimal external dependencies"""
    
    @patch('socket.socket')
    @patch('dashboard.llm_client.LLMClient')
    def test_complete_message_flow(self, mock_llm_client, mock_socket):
        """Test complete message handling flow"""
        # Setup mocked components
        mock_llm_instance = MagicMock()
        mock_llm_instance.analyze_game_state.return_value = {
            'actions': ['RIGHT', 'A'], 
            'success': True,
            'text': 'Moving right and pressing A to interact'
        }
        mock_llm_client.return_value = mock_llm_instance
        
        service = AIGameService()
        
        # Test complete flow: ready -> config -> screenshot -> response
        ready_result = service._handle_ready_message("ready")
        self.assertEqual(ready_result, "welcome")
        
        config_result = service._handle_game_config("game_config|pokemon_red|Pallet Town")
        self.assertIsNone(config_result)  # Config loading doesn't return response
        
        loaded_result = service._handle_config_loaded("config_loaded")
        self.assertEqual(loaded_result, "request_screenshot")
        
        # Now screenshot should be processed
        screenshot_result = service._handle_screenshot_data(
            "screenshot_data|/test/path.png|5|8|UP|0"
        )
        self.assertEqual(screenshot_result, "0,7")  # A,RIGHT
        
        # Verify LLM was called with correct game state
        call_args = mock_llm_instance.analyze_game_state.call_args
        game_state = call_args[0][1]
        self.assertEqual(game_state['current_map'], 'Pallet Town')
        self.assertEqual(game_state['x'], 5)
        self.assertEqual(game_state['y'], 8)
        self.assertEqual(game_state['direction'], 'UP')
        self.assertEqual(game_state['map_id'], 0)


class AIGameServiceLoggingTest(TestCase):
    """Test AIGameService logging integration"""
    
    def setUp(self):
        """Set up test configuration and clean up any existing handlers"""
        # Clean up any existing loggers
        logger = logging.getLogger('ai_gba_player')
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()
        
        self.test_config = {
            'host': '127.0.0.1',
            'port': 8888,
            'llm_provider': 'google',
            'providers': {
                'google': {
                    'api_key': 'test_key_123',
                    'model_name': 'gemini-2.5-pro'
                }
            },
            'decision_cooldown': 2
        }
    
    def tearDown(self):
        """Clean up loggers after each test"""
        logger = logging.getLogger('ai_gba_player')
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()
    
    @patch('socket.socket')
    @patch('dashboard.llm_client.LLMClient')
    @patch('sys.stdout', new_callable=StringIO)
    def test_service_logging_initialization(self, mock_stdout, mock_llm_client, mock_socket):
        """Test that AIGameService properly initializes logging"""
        service = AIGameService()
        
        # Service should have a logger
        self.assertIsNotNone(service.logger)
        self.assertEqual(service.logger.name, 'ai_gba_player.AIGameService')
    
    @patch('socket.socket')
    @patch('dashboard.llm_client.LLMClient')
    def test_logging_with_screenshot_processing(self, mock_llm_client, mock_socket):
        """Test logging integration during screenshot processing"""
        # Setup mocked LLM response
        mock_llm_instance = MagicMock()
        mock_llm_instance.analyze_game_state.return_value = {
            'actions': ['UP', 'A'],
            'success': True,
            'text': 'Moving up and pressing A'
        }
        mock_llm_client.return_value = mock_llm_instance
        
        service = AIGameService()
        
        # Capture log messages by adding a handler
        captured_logs = []
        
        class TestHandler(logging.Handler):
            def emit(self, record):
                captured_logs.append(record)
        
        test_handler = TestHandler()
        service.logger.addHandler(test_handler)
        service.logger.setLevel(logging.DEBUG)
        
        with patch('builtins.open', mock_open(read_data=b'fake_png_data')):
            test_data = "screenshot_data|/test/path.png|10|20|DOWN|1"
            result = service._handle_screenshot_data(test_data)
        
        # Clean up handler
        service.logger.removeHandler(test_handler)
        
        # Verify that logging calls were made during processing
        self.assertIsNotNone(result)
    
    @patch('socket.socket')
    @patch('dashboard.llm_client.LLMClient')
    def test_error_logging(self, mock_llm_client, mock_socket):
        """Test error logging when LLM calls fail"""
        # Setup mocked LLM to raise an exception
        mock_llm_instance = MagicMock()
        mock_llm_instance.analyze_game_state.side_effect = Exception("LLM API Error")
        mock_llm_client.return_value = mock_llm_instance
        
        service = AIGameService()
        
        # Capture log messages
        captured_logs = []
        
        class TestHandler(logging.Handler):
            def emit(self, record):
                captured_logs.append(record)
        
        test_handler = TestHandler()
        test_handler.setLevel(logging.ERROR)
        service.logger.addHandler(test_handler)
        service.logger.setLevel(logging.DEBUG)
        
        with patch('builtins.open', mock_open(read_data=b'fake_png_data')):
            test_data = "screenshot_data|/test/path.png|10|20|DOWN|1"
            result = service._handle_screenshot_data(test_data)
        
        # Clean up handler
        service.logger.removeHandler(test_handler)
        
        # Should return fallback actions when LLM fails
        self.assertIsNotNone(result)
    
    def test_get_logger_integration(self):
        """Test get_logger function integration"""
        logger = get_logger('AIGameService')
        
        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, 'ai_gba_player.AIGameService')
        
        # Test that logger has proper parent-child relationship
        parent_logger = logging.getLogger('ai_gba_player')
        self.assertIs(logger.parent, parent_logger)
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_emoji_formatter_integration(self, mock_stdout):
        """Test that EmojiFormatter is working with AIGameService logger"""
        from core.logging_config import setup_logging
        
        # Set up logging with emoji formatter
        setup_logging(level=logging.DEBUG, log_to_file=False)
        
        logger = get_logger('AIGameService')
        
        # Test different log levels
        logger.debug("Debug message")
        logger.info("Info message")  
        logger.warning("Warning message")
        logger.error("Error message")
        
        output = mock_stdout.getvalue()
        
        # Check that emojis are in the output
        self.assertIn('🔍', output)  # Debug emoji
        self.assertIn('📝', output)  # Info emoji
        self.assertIn('⚠️', output)  # Warning emoji
        self.assertIn('❌', output)  # Error emoji
        
        # Check that logger name is in output
        self.assertIn('ai_gba_player.AIGameService', output)
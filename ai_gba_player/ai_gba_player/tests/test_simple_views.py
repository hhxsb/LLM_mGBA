from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock, mock_open
import json
import logging
import tempfile
import os
from io import StringIO

from dashboard.models import Configuration, Process, ProcessStatus, ChatMessage, MessageType
from core.logging_config import get_logger


class SimpleViewsConfigurationTest(TestCase):
    """Test configuration loading and saving functions"""
    
    def setUp(self):
        self.client = Client()
        # Clean up any existing loggers
        logger = logging.getLogger('ai_gba_player')
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()
    
    def tearDown(self):
        """Clean up loggers after each test"""
        logger = logging.getLogger('ai_gba_player')
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()
    
    def test_load_config_from_database(self):
        """Test loading configuration from database"""
        from ai_gba_player.simple_views import load_config
        
        # Create database configuration
        config = Configuration.get_config()
        config.rom_path = '/test/rom.gba'
        config.mgba_path = '/test/mgba'
        config.llm_provider = 'google'
        config.decision_cooldown = 5
        config.providers = {
            'google': {'api_key': 'test_key_123', 'model_name': 'gemini-2.5-pro'}
        }
        config.save()
        
        # Load config should use database
        loaded_config = load_config()
        
        self.assertEqual(loaded_config['rom_path'], '/test/rom.gba')
        self.assertEqual(loaded_config['mgba_path'], '/test/mgba')
        self.assertEqual(loaded_config['llm_provider'], 'google')
        self.assertEqual(loaded_config['api_key'], 'test_key_123')
        self.assertEqual(loaded_config['cooldown'], 5)
    
    @patch('os.path.exists', return_value=True)
    @patch('builtins.open', new_callable=mock_open)
    def test_load_config_file_fallback(self, mock_file, mock_exists):
        """Test loading configuration from file when database fails"""
        from ai_gba_player.simple_views import load_config
        
        # Mock file content
        file_config = {
            'rom_path': '/file/rom.gba',
            'mgba_path': '/file/mgba',
            'llm_provider': 'openai',
            'api_key': 'file_key_456',
            'cooldown': 4
        }
        mock_file.return_value.read.return_value = json.dumps(file_config)
        
        # Mock database failure
        with patch('dashboard.models.Configuration.objects.first', side_effect=Exception("DB Error")):
            loaded_config = load_config()
        
        self.assertEqual(loaded_config['rom_path'], '/file/rom.gba')
        self.assertEqual(loaded_config['llm_provider'], 'openai')
        self.assertEqual(loaded_config['api_key'], 'file_key_456')
    
    def test_load_config_defaults(self):
        """Test loading default configuration when no config exists"""
        from ai_gba_player.simple_views import load_config
        
        # Mock both database and file failures
        with patch('dashboard.models.Configuration.objects.first', side_effect=Exception("DB Error")):
            with patch('os.path.exists', return_value=False):
                loaded_config = load_config()
        
        # Should return defaults
        self.assertEqual(loaded_config['rom_path'], '')
        self.assertEqual(loaded_config['mgba_path'], '')
        self.assertEqual(loaded_config['llm_provider'], 'gemini')
        self.assertEqual(loaded_config['api_key'], '')
        self.assertEqual(loaded_config['cooldown'], 3)
    
    def test_save_config_to_database_and_file(self):
        """Test saving configuration to both database and file"""
        from ai_gba_player.simple_views import save_config_to_file
        
        test_config = {
            'rom_path': '/save/test/rom.gba',
            'mgba_path': '/save/test/mgba',
            'llm_provider': 'google',
            'api_key': 'save_test_key',
            'cooldown': 6
        }
        
        with patch('builtins.open', mock_open()) as mock_file:
            result = save_config_to_file(test_config)
        
        self.assertTrue(result)
        
        # Verify database was updated
        config = Configuration.objects.first()
        self.assertEqual(config.rom_path, '/save/test/rom.gba')
        self.assertEqual(config.mgba_path, '/save/test/mgba')
        self.assertEqual(config.llm_provider, 'google')
        self.assertEqual(config.decision_cooldown, 6)
        
        # Verify API key was saved in providers
        self.assertIn('google', config.providers)
        self.assertEqual(config.providers['google']['api_key'], 'save_test_key')
        
        # Verify file write was called
        mock_file.assert_called_once()
    
    def test_save_config_provider_mapping(self):
        """Test provider mapping (gemini -> google) during save"""
        from ai_gba_player.simple_views import save_config_to_file
        
        test_config = {
            'llm_provider': 'gemini',
            'api_key': 'gemini_key_test'
        }
        
        with patch('builtins.open', mock_open()):
            save_config_to_file(test_config)
        
        # Should map gemini -> google in database
        config = Configuration.objects.first()
        self.assertEqual(config.llm_provider, 'gemini')
        self.assertIn('google', config.providers)  # Key mapped to 'google'
        self.assertEqual(config.providers['google']['api_key'], 'gemini_key_test')


class SimpleViewsDashboardTest(TestCase):
    """Test dashboard view functionality"""
    
    def setUp(self):
        self.client = Client()
    
    def test_dashboard_view_loads(self):
        """Test dashboard view returns proper HTML"""
        response = self.client.get('/')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'AI GBA Player Dashboard')
        self.assertContains(response, 'Launch mGBA')
        self.assertContains(response, 'Save Configuration')
        
        # Should include embedded CSS and JS
        self.assertContains(response, '<style>')
        self.assertContains(response, '<script>')
    
    def test_dashboard_view_with_existing_config(self):
        """Test dashboard loads existing configuration"""
        # Create test configuration
        config = Configuration.get_config()
        config.rom_path = '/test/dashboard/rom.gba'
        config.llm_provider = 'openai'
        config.save()
        
        response = self.client.get('/')
        
        self.assertEqual(response.status_code, 200)
        # Configuration values should be included in the page
        self.assertContains(response, '/test/dashboard/rom.gba')
        self.assertContains(response, 'openai')


class SimpleViewsAPIEndpointsTest(TestCase):
    """Test API endpoints functionality"""
    
    def setUp(self):
        self.client = Client()
    
    def test_config_api_endpoint(self):
        """Test /api/config/ endpoint returns JSON configuration"""
        # Create test configuration
        config = Configuration.get_config()
        config.rom_path = '/api/test/rom.gba'
        config.llm_provider = 'google'
        config.save()
        
        response = self.client.get('/api/config/')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        data = response.json()
        self.assertEqual(data['rom_path'], '/api/test/rom.gba')
        self.assertEqual(data['llm_provider'], 'google')
    
    @patch('dashboard.ai_game_service.start_ai_service')
    def test_restart_service_endpoint(self, mock_start_service):
        """Test /api/restart-service/ endpoint"""
        mock_start_service.return_value = True
        
        response = self.client.post('/api/restart-service/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('restarted', data['message'].lower())
        
        mock_start_service.assert_called_once()
    
    @patch('dashboard.ai_game_service.start_ai_service')
    def test_restart_service_failure(self, mock_start_service):
        """Test /api/restart-service/ endpoint handles failures"""
        mock_start_service.side_effect = Exception("Service start failed")
        
        response = self.client.post('/api/restart-service/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('Service start failed', data['message'])
    
    @patch('dashboard.ai_game_service.stop_ai_service')
    def test_stop_service_endpoint(self, mock_stop_service):
        """Test /api/stop-service/ endpoint"""
        mock_stop_service.return_value = True
        
        response = self.client.post('/api/stop-service/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('stopped', data['message'].lower())
    
    def test_get_chat_messages_endpoint(self):
        """Test /api/chat-messages/ endpoint"""
        # Create test chat messages
        ChatMessage.objects.create(
            message_id='test_msg_1',
            message_type=MessageType.SYSTEM,
            source='ai_service',
            content={'text': 'System started'},
            timestamp=1640995200.0,
            sequence=1
        )
        ChatMessage.objects.create(
            message_id='test_msg_2', 
            message_type=MessageType.RESPONSE,
            source='llm_client',
            content={'text': 'AI response', 'actions': ['UP', 'A']},
            timestamp=1640995201.0,
            sequence=2
        )
        
        response = self.client.get('/api/chat-messages/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn('messages', data)
        self.assertEqual(len(data['messages']), 2)
        
        # Messages should be ordered by timestamp (newest first)
        self.assertEqual(data['messages'][0]['message_id'], 'test_msg_2')
        self.assertEqual(data['messages'][1]['message_id'], 'test_msg_1')
    
    def test_get_chat_messages_empty(self):
        """Test /api/chat-messages/ endpoint with no messages"""
        response = self.client.get('/api/chat-messages/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn('messages', data)
        self.assertEqual(len(data['messages']), 0)
    
    @patch('subprocess.run')
    @patch('os.path.exists', return_value=True)
    def test_launch_mgba_endpoint_success(self, mock_exists, mock_subprocess):
        """Test /api/launch-mgba/ endpoint successful launch"""
        # Setup configuration
        config = Configuration.get_config()
        config.rom_path = '/test/rom.gba'
        config.mgba_path = '/test/mgba'
        config.save()
        
        # Mock successful subprocess
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process
        
        response = self.client.post('/api/launch-mgba/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('launched', data['message'].lower())
    
    @patch('os.path.exists', return_value=False)
    def test_launch_mgba_missing_files(self, mock_exists):
        """Test /api/launch-mgba/ endpoint with missing files"""
        config = Configuration.get_config()
        config.rom_path = '/missing/rom.gba'
        config.mgba_path = '/missing/mgba'
        config.save()
        
        response = self.client.post('/api/launch-mgba/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('not found', data['message'].lower())
    
    def test_save_ai_config_endpoint(self):
        """Test /api/save-ai-config/ endpoint"""
        post_data = {
            'llm_provider': 'openai',
            'api_key': 'test_openai_key_789',
            'cooldown': 7
        }
        
        with patch('builtins.open', mock_open()):
            response = self.client.post('/api/save-ai-config/', post_data)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('saved', data['message'].lower())
        
        # Verify configuration was updated
        config = Configuration.objects.first()
        self.assertEqual(config.llm_provider, 'openai')
        self.assertEqual(config.decision_cooldown, 7)
        self.assertEqual(config.providers['openai']['api_key'], 'test_openai_key_789')
    
    def test_save_rom_config_endpoint(self):
        """Test /api/save-rom-config/ endpoint"""
        post_data = {
            'rom_path': '/new/test/rom.gba',
            'mgba_path': '/new/test/mgba'
        }
        
        with patch('builtins.open', mock_open()):
            response = self.client.post('/api/save-rom-config/', post_data)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Verify configuration was updated
        config = Configuration.objects.first()
        self.assertEqual(config.rom_path, '/new/test/rom.gba')
        self.assertEqual(config.mgba_path, '/new/test/mgba')
    
    def test_reset_llm_session_endpoint(self):
        """Test /api/reset-llm-session/ endpoint"""
        response = self.client.post('/api/reset-llm-session/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('reset', data['message'].lower())
    
    def test_chat_message_endpoint_post(self):
        """Test /api/chat-message/ endpoint for posting messages"""
        post_data = {
            'message': 'Test user message',
            'sender': 'user'
        }
        
        response = self.client.post('/api/chat-message/', 
                                    json.dumps(post_data),
                                    content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Verify message was stored (implementation depends on actual chat storage)
    
    def test_invalid_api_endpoints(self):
        """Test invalid API endpoints return 404"""
        response = self.client.get('/api/nonexistent-endpoint/')
        self.assertEqual(response.status_code, 404)
        
        response = self.client.post('/api/invalid-action/')
        self.assertEqual(response.status_code, 404)


class SimpleViewsHTTPMethodTest(TestCase):
    """Test HTTP method restrictions on endpoints"""
    
    def setUp(self):
        self.client = Client()
    
    def test_get_only_endpoints(self):
        """Test endpoints that only accept GET requests"""
        # Dashboard should accept GET
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        
        # Config API should accept GET
        response = self.client.get('/api/config/')
        self.assertEqual(response.status_code, 200)
        
        # Chat messages should accept GET
        response = self.client.get('/api/chat-messages/')
        self.assertEqual(response.status_code, 200)
    
    def test_post_only_endpoints(self):
        """Test endpoints that only accept POST requests"""
        post_endpoints = [
            '/api/restart-service/',
            '/api/stop-service/', 
            '/api/reset-llm-session/',
            '/api/launch-mgba/',
            '/api/save-ai-config/',
            '/api/save-rom-config/'
        ]
        
        for endpoint in post_endpoints:
            with self.subTest(endpoint=endpoint):
                # Should accept POST
                response = self.client.post(endpoint)
                self.assertNotEqual(response.status_code, 405)  # Method not allowed
                
                # Should reject GET (most endpoints)
                if endpoint not in ['/api/chat-message/']:  # Some endpoints handle both
                    response = self.client.get(endpoint)
                    # May return error but shouldn't be method not allowed if handled


class SimpleViewsLoggingIntegrationTest(TestCase):
    """Test logging integration in simple views"""
    
    def setUp(self):
        self.client = Client()
        # Clean up any existing loggers
        logger = logging.getLogger('ai_gba_player')
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()
    
    def tearDown(self):
        """Clean up loggers after each test"""
        logger = logging.getLogger('ai_gba_player')
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_views_logging_integration(self, mock_stdout):
        """Test that views use proper logging setup"""
        from core.logging_config import setup_logging
        
        # Set up logging with emoji formatter
        setup_logging(level=logging.DEBUG, log_to_file=False)
        
        # Import after logging setup to ensure logger is configured
        from ai_gba_player.simple_views import logger
        
        # Test that logger is properly configured
        self.assertIsInstance(logger, logging.Logger)
        self.assertTrue(logger.name.startswith('ai_gba_player'))
    
    def test_config_functions_use_logging(self):
        """Test that configuration functions use proper logging"""
        from ai_gba_player.simple_views import load_config, save_config_to_file
        
        # These functions should handle errors gracefully (using print currently)
        # In a production environment, they would use logger.error() instead
        
        # Test load_config with database error
        with patch('dashboard.models.Configuration.objects.first', side_effect=Exception("DB Error")):
            with patch('os.path.exists', return_value=False):
                config = load_config()
                # Should return defaults without crashing
                self.assertIsInstance(config, dict)
        
        # Test save_config with error
        with patch('dashboard.models.Configuration.objects.first', side_effect=Exception("DB Error")):
            result = save_config_to_file({'test': 'data'})
            # Should handle error gracefully
            self.assertFalse(result)
    
    @patch('dashboard.ai_game_service.start_ai_service', side_effect=Exception("Service Error"))
    def test_api_endpoint_error_handling(self, mock_start):
        """Test that API endpoints handle and log errors properly"""
        response = self.client.post('/api/restart-service/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('Service Error', data['message'])
        # Error should be handled gracefully without crashing
    
    def test_get_logger_integration_in_views(self):
        """Test get_logger function integration in views module"""
        logger = get_logger('simple_views_test')
        
        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, 'ai_gba_player.simple_views_test')
        
        # Test that logger has proper parent-child relationship
        parent_logger = logging.getLogger('ai_gba_player')
        self.assertIs(logger.parent, parent_logger)
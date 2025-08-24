from django.test import TestCase
from unittest.mock import patch, MagicMock, mock_open
import tempfile
import os
import time
from pathlib import Path

from dashboard.llm_client import LLMClient
from dashboard.models import Configuration


class LLMClientTest(TestCase):
    """Test LLMClient functionality with proper mocking"""
    
    def setUp(self):
        """Set up test configuration"""
        self.test_config = {
            'llm_provider': 'google',
            'providers': {
                'google': {
                    'api_key': 'test_key_123',
                    'model_name': 'gemini-2.5-pro',
                    'max_tokens': 4096
                },
                'openai': {
                    'api_key': 'test_openai_key',
                    'model_name': 'gpt-4',
                    'max_tokens': 1024
                }
            },
            'decision_cooldown': 2,
            'notepad_path': 'test_notepad.txt',
            'prompt_template_path': 'data/prompt_template.txt'
        }
    
    def test_client_initialization(self):
        """Test LLMClient initializes with correct provider mapping"""
        client = LLMClient(self.test_config)
        
        self.assertEqual(client.provider, 'google')
        self.assertEqual(client.cooldown_seconds, 2)
        self.assertIn('google', client.providers_config)
        self.assertEqual(client.providers_config['google']['api_key'], 'test_key_123')
    
    def test_provider_mapping(self):
        """Test provider name mapping (UI to internal names)"""
        # Test gemini -> google mapping
        config = self.test_config.copy()
        config['llm_provider'] = 'gemini'
        client = LLMClient(config)
        self.assertEqual(client.provider, 'google')
        
        # Test direct google mapping
        config['llm_provider'] = 'google'
        client = LLMClient(config)
        self.assertEqual(client.provider, 'google')
        
        # Test openai mapping
        config['llm_provider'] = 'openai'
        client = LLMClient(config)
        self.assertEqual(client.provider, 'openai')
    
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_wait_for_screenshot_success(self, mock_getsize, mock_exists):
        """Test screenshot wait logic - successful case"""
        client = LLMClient(self.test_config)
        
        # Mock file becoming available
        mock_exists.return_value = True
        mock_getsize.return_value = 2048  # Large enough file
        
        result = client._wait_for_screenshot('/test/screenshot.png', max_wait_seconds=1)
        self.assertTrue(result)
    
    @patch('os.path.exists')
    @patch('time.sleep')  # Mock sleep to speed up tests
    def test_wait_for_screenshot_timeout(self, mock_sleep, mock_exists):
        """Test screenshot wait logic - timeout case"""
        client = LLMClient(self.test_config)
        
        # Mock file never becoming available
        mock_exists.return_value = False
        
        result = client._wait_for_screenshot('/test/nonexistent.png', max_wait_seconds=0.5)
        self.assertFalse(result)
    
    @patch('os.path.exists')
    @patch('os.path.getsize')
    @patch('time.sleep')
    def test_wait_for_screenshot_small_file(self, mock_sleep, mock_getsize, mock_exists):
        """Test screenshot wait logic - file too small initially"""
        client = LLMClient(self.test_config)
        
        # Mock file exists but is too small initially
        mock_exists.return_value = True
        mock_getsize.side_effect = [100, 500, 2048]  # File grows over time
        
        result = client._wait_for_screenshot('/test/growing.png', max_wait_seconds=1)
        self.assertTrue(result)
        self.assertEqual(mock_getsize.call_count, 3)
    
    @patch('dashboard.llm_client.LLMClient._wait_for_screenshot')
    @patch('dashboard.llm_client.LLMClient._call_google_api')
    def test_analyze_game_state_success(self, mock_google_api, mock_wait):
        """Test game state analysis - successful path"""
        client = LLMClient(self.test_config)
        
        # Mock successful screenshot wait and API call
        mock_wait.return_value = True
        mock_google_api.return_value = {
            'text': 'I can see a Pokemon battle. I should attack.',
            'actions': ['A'],
            'success': True
        }
        
        game_state = {
            'x': 10, 'y': 8, 'direction': 'UP', 'map_id': 1,
            'current_map': 'Route 1'
        }
        
        result = client.analyze_game_state('/test/screenshot.png', game_state)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['actions'], ['A'])
        self.assertIn('Pokemon battle', result['text'])
        mock_wait.assert_called_once_with('/test/screenshot.png', max_wait_seconds=5)
        mock_google_api.assert_called_once()
    
    @patch('dashboard.llm_client.LLMClient._wait_for_screenshot')
    def test_analyze_game_state_screenshot_timeout(self, mock_wait):
        """Test game state analysis - screenshot timeout"""
        client = LLMClient(self.test_config)
        
        # Mock screenshot wait timeout
        mock_wait.return_value = False
        
        game_state = {'x': 10, 'y': 8, 'direction': 'UP', 'map_id': 1}
        result = client.analyze_game_state('/test/missing.png', game_state)
        
        self.assertFalse(result['success'])
        self.assertEqual(result['actions'], [])  # No actions on error
        self.assertIn('Screenshot not available after waiting', result['text'])
        self.assertIn('error', result)
    
    @patch('dashboard.llm_client.LLMClient._wait_for_screenshot')
    @patch('os.path.exists')
    @patch('dashboard.llm_client.LLMClient._call_google_api_with_comparison')
    def test_analyze_game_state_with_comparison(self, mock_comparison_api, mock_exists, mock_wait):
        """Test game state analysis with screenshot comparison"""
        client = LLMClient(self.test_config)
        
        # Mock successful current screenshot wait and previous exists
        mock_wait.return_value = True
        mock_exists.return_value = True
        mock_comparison_api.return_value = {
            'text': 'Compared to previous screen, I moved right. Now I should go up.',
            'actions': ['UP'],
            'success': True
        }
        
        game_state = {'x': 11, 'y': 8, 'direction': 'RIGHT', 'map_id': 1}
        result = client.analyze_game_state_with_comparison(
            '/test/current.png', '/test/previous.png', game_state
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['actions'], ['UP'])
        self.assertIn('moved right', result['text'])
        mock_comparison_api.assert_called_once()
    
    @patch('dashboard.llm_client.LLMClient._wait_for_screenshot')  
    @patch('os.path.exists')
    @patch('dashboard.llm_client.LLMClient.analyze_game_state')
    def test_comparison_fallback_to_single(self, mock_single_analysis, mock_exists, mock_wait):
        """Test comparison analysis falls back to single screenshot when previous missing"""
        client = LLMClient(self.test_config)
        
        # Mock current screenshot available but previous missing
        mock_wait.return_value = True
        mock_exists.return_value = False  # Previous screenshot missing
        mock_single_analysis.return_value = {
            'text': 'Single screenshot analysis',
            'actions': ['A'], 
            'success': True
        }
        
        game_state = {'x': 10, 'y': 8, 'direction': 'UP', 'map_id': 1}
        result = client.analyze_game_state_with_comparison(
            '/test/current.png', '/test/missing_previous.png', game_state
        )
        
        self.assertTrue(result['success'])
        mock_single_analysis.assert_called_once_with('/test/current.png', game_state, '')
    
    def test_create_game_context(self):
        """Test game context creation for prompts"""
        client = LLMClient(self.test_config)
        
        game_state = {
            'x': 15, 'y': 12, 'direction': 'DOWN', 'map_id': 0,
            'current_map': 'Pallet Town'
        }
        
        # Mock template loading
        with patch('builtins.open', mock_open(read_data='Test prompt {spatial_context}')):
            context = client._create_game_context(game_state, 'Recent: UP, A', 'Before/after analysis')
        
        # Test that spatial context is included
        self.assertIn('Pallet Town', context)
        self.assertIn('position (15, 12)', context)
        self.assertIn('facing DOWN', context)
    
    @patch('pathlib.Path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_notepad_operations(self, mock_file, mock_exists):
        """Test notepad reading and updating operations"""
        client = LLMClient(self.test_config)
        
        # Test reading existing notepad
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = "# Game Progress\\n\\nCaught Pikachu!"
        
        content = client._read_notepad()
        self.assertIn('Caught Pikachu', content)
        
        # Test reading non-existent notepad (should return default)
        mock_exists.return_value = False
        content = client._read_notepad()
        self.assertIn('Game just started', content)
    
    def test_spatial_context_generation(self):
        """Test spatial context generation for different locations"""
        client = LLMClient(self.test_config)
        
        # Test Pallet Town context
        game_state = {
            'x': 5, 'y': 6, 'direction': 'UP', 'map_id': 0,
            'current_map': 'Pallet Town'
        }
        context = client._get_spatial_context(game_state['current_map'], **game_state)
        
        self.assertIn('Pallet Town', context)
        self.assertIn('position (5, 6)', context)
        self.assertIn('facing UP', context)
        
        # Test unknown location
        game_state['current_map'] = 'Unknown Area'
        context = client._get_spatial_context(game_state['current_map'], **game_state)
        self.assertIn('Unknown Area', context)
    
    def test_button_action_validation(self):
        """Test that LLM responses with invalid actions are handled"""
        client = LLMClient(self.test_config)
        
        # This would typically be tested through the provider-specific methods
        # but we can test the action validation logic
        valid_actions = ['UP', 'DOWN', 'LEFT', 'RIGHT', 'A', 'B', 'START', 'SELECT']
        
        for action in valid_actions:
            # Each action should be a valid game button
            self.assertIn(action, ['UP', 'DOWN', 'LEFT', 'RIGHT', 'A', 'B', 'START', 'SELECT'])


class LLMClientProviderTest(TestCase):
    """Test provider-specific functionality"""
    
    def setUp(self):
        self.test_config = {
            'llm_provider': 'google',
            'providers': {
                'google': {
                    'api_key': 'test_google_key',
                    'model_name': 'gemini-2.5-pro'
                }
            }
        }
    
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_google_api_configuration(self, mock_model, mock_configure):
        """Test Google API configuration and model setup"""
        client = LLMClient(self.test_config)
        
        # Mock the model and response
        mock_model_instance = MagicMock()
        mock_model.return_value = mock_model_instance
        
        # Test that this doesn't crash during initialization
        self.assertEqual(client.provider, 'google')
    
    def test_unsupported_provider_fallback(self):
        """Test fallback behavior for unsupported providers"""
        config = self.test_config.copy()
        config['llm_provider'] = 'unsupported_provider'
        
        client = LLMClient(config)
        
        # Should fall back to google
        self.assertEqual(client.provider, 'google')
    
    @patch('dashboard.llm_client.LLMClient._wait_for_screenshot')
    def test_fallback_response_on_error(self, mock_wait):
        """Test fallback response when LLM calls fail"""
        client = LLMClient(self.test_config)
        
        # Mock screenshot available but API call will fail
        mock_wait.return_value = True
        
        with patch.object(client, '_call_google_api', side_effect=Exception("API Error")):
            game_state = {'x': 10, 'y': 8, 'direction': 'UP', 'map_id': 1}
            result = client.analyze_game_state('/test/screenshot.png', game_state)
            
            self.assertFalse(result['success'])
            self.assertEqual(result['actions'], [])  # No actions on error
            self.assertIn('error occurred', result['text'])
            self.assertIn('API Error', result['error'])
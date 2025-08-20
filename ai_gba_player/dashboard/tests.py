from django.test import TestCase, Client
from django.urls import reverse
from .models import Configuration, Process


class ConfigurationTestCase(TestCase):
    """Test Configuration model functionality"""
    
    def test_get_config_creates_default(self):
        """Test that get_config creates a default configuration"""
        config = Configuration.get_config()
        self.assertIsNotNone(config)
        self.assertEqual(config.llm_provider, 'google')
    
    def test_to_dict_conversion(self):
        """Test configuration conversion to dictionary"""
        config = Configuration.get_config()
        config_dict = config.to_dict()
        self.assertIsInstance(config_dict, dict)
        self.assertIn('llm_provider', config_dict)
        self.assertIn('decision_cooldown', config_dict)


class ProcessTestCase(TestCase):
    """Test Process model functionality"""
    
    def test_create_process(self):
        """Test process creation"""
        from .models import ProcessStatus
        process = Process.objects.create(
            name='test_service',
            status=ProcessStatus.RUNNING
        )
        self.assertIsNotNone(process)
        self.assertEqual(process.name, 'test_service')
        self.assertEqual(process.status, ProcessStatus.RUNNING)


class ViewTestCase(TestCase):
    """Test API endpoints"""
    
    def setUp(self):
        self.client = Client()
    
    def test_dashboard_view(self):
        """Test dashboard page loads"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
    
    def test_api_chat_messages(self):
        """Test chat messages API endpoint"""
        response = self.client.get('/api/chat-messages/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('messages', response.json())
    
    def test_api_endpoints_accessible(self):
        """Test that API endpoints exist"""
        response = self.client.get('/api/chat-messages/')
        self.assertEqual(response.status_code, 200)
        
        # Test that the response has the expected structure
        data = response.json()
        self.assertIn('messages', data)
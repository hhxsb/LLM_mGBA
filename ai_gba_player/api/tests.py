from django.test import TestCase, Client
from django.urls import reverse
import json


class APITestCase(TestCase):
    """Test API functionality"""
    
    def setUp(self):
        self.client = Client()
    
    def test_api_endpoints_exist(self):
        """Test that API endpoints are accessible"""
        endpoints = [
            '/api/chat-messages/',
        ]
        
        for endpoint in endpoints:
            response = self.client.get(endpoint)
            # Should not return 404
            self.assertNotEqual(response.status_code, 404, 
                              f"Endpoint {endpoint} not found")
    
    def test_chat_messages_format(self):
        """Test chat messages API returns expected format"""
        response = self.client.get('/api/chat-messages/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('messages', data)
        self.assertIsInstance(data['messages'], list)
    
    def test_api_functionality(self):
        """Test that API returns valid responses"""
        response = self.client.get('/api/chat-messages/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIsInstance(data, dict)
        self.assertIn('messages', data)
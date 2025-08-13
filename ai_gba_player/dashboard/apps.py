from django.apps import AppConfig
import sys
from pathlib import Path


class DashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dashboard'

    def ready(self):
        """Initialize the dashboard app and set up AI service integration."""
        # Import and initialize the AI service integration
        try:
            from dashboard.ai_game_service import get_ai_service
            print("✅ AI Game Service integration ready")
        except ImportError as e:
            print(f"⚠️ Warning: Could not import AI service: {e}")

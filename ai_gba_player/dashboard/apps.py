from django.apps import AppConfig
import sys
from pathlib import Path


class DashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dashboard'

    def ready(self):
        """Initialize the dashboard app and set up unified service integration."""
        # Add project root to path for unified service imports
        project_root = Path(__file__).parent.parent.parent
        sys.path.append(str(project_root))
        sys.path.append(str(project_root / 'ai_gba_player'))
        
        # Import and initialize the unified service integration
        try:
            from core.unified_game_service import get_unified_service
            print("✅ Unified Game Service integration ready")
        except ImportError:
            try:
                from ai_gba_player.core.unified_game_service import get_unified_service
                print("✅ Unified Game Service integration ready")
            except ImportError as e:
                print(f"⚠️ Warning: Could not import unified service: {e}")

"""
Service Manager for AI Game Service

Provides proper object-oriented encapsulation for AI service lifecycle management.
Follows singleton pattern for service instance management.
"""

import time
from typing import Optional
from threading import Lock

from .ai_game_service import AIGameService


class AIGameServiceManager:
    """
    Manages the lifecycle of the AI Game Service with proper encapsulation.
    
    Implements singleton pattern to ensure only one service instance can run at a time.
    Provides thread-safe operations for service management.
    """
    
    _instance: Optional['AIGameServiceManager'] = None
    _lock = Lock()
    
    def __new__(cls) -> 'AIGameServiceManager':
        """Ensure singleton instance"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize service manager (called only once due to singleton)"""
        if self._initialized:
            return
            
        self._service_instance: Optional[AIGameService] = None
        self._service_lock = Lock()
        self._initialized = True
    
    def start_service(self) -> bool:
        """
        Start the AI service if not already running.
        
        Returns:
            bool: True if service started successfully or was already running
        """
        with self._service_lock:
            try:
                if self._service_instance and self._service_instance.is_alive():
                    print("⚠️ AI service is already running")
                    return True
                
                self._service_instance = AIGameService()
                self._service_instance.start()
                
                # Give service time to initialize
                time.sleep(0.5)
                
                if self._service_instance.is_alive():
                    print("✅ AI service started successfully")
                    return True
                else:
                    print("❌ AI service failed to start properly")
                    self._service_instance = None
                    return False
                    
            except Exception as e:
                print(f"❌ Failed to start AI service: {e}")
                self._service_instance = None
                return False
    
    def stop_service(self) -> bool:
        """
        Stop the AI service if running.
        
        Returns:
            bool: True if service stopped successfully or was not running
        """
        with self._service_lock:
            try:
                if self._service_instance:
                    self._service_instance.stop()
                    
                    # Wait for service to stop cleanly
                    timeout = 5.0
                    start_time = time.time()
                    while (self._service_instance.is_alive() and 
                           (time.time() - start_time) < timeout):
                        time.sleep(0.1)
                    
                    if self._service_instance.is_alive():
                        print("⚠️ AI service did not stop within timeout")
                    
                    self._service_instance = None
                
                print("✅ AI service stopped")
                return True
                
            except Exception as e:
                print(f"❌ Failed to stop AI service: {e}")
                return False
    
    def restart_service(self) -> bool:
        """
        Restart the AI service (stop then start).
        
        Returns:
            bool: True if service restarted successfully
        """
        print("🔄 Restarting AI service...")
        if not self.stop_service():
            return False
        
        # Brief pause between stop and start
        time.sleep(1.0)
        
        return self.start_service()
    
    def is_service_running(self) -> bool:
        """
        Check if the AI service is currently running.
        
        Returns:
            bool: True if service is running and alive
        """
        with self._service_lock:
            return (self._service_instance is not None and 
                    self._service_instance.is_alive())
    
    def get_service(self) -> Optional[AIGameService]:
        """
        Get the current AI service instance.
        
        Returns:
            Optional[AIGameService]: Current service instance or None if not running
        """
        with self._service_lock:
            if self._service_instance and self._service_instance.is_alive():
                return self._service_instance
            return None
    
    def get_service_status(self) -> dict:
        """
        Get detailed service status information.
        
        Returns:
            dict: Status information including running state, uptime, etc.
        """
        with self._service_lock:
            if not self._service_instance:
                return {
                    'running': False,
                    'status': 'stopped',
                    'uptime': 0,
                    'connections': 0
                }
            
            is_alive = self._service_instance.is_alive()
            status = {
                'running': is_alive,
                'status': 'running' if is_alive else 'stopped',
                'connections': getattr(self._service_instance, 'active_connections', 0)
            }
            
            # Calculate uptime if service has start time
            if hasattr(self._service_instance, 'start_time'):
                status['uptime'] = time.time() - self._service_instance.start_time
            else:
                status['uptime'] = 0
                
            return status
    
    def reload_service_config(self) -> bool:
        """
        Reload configuration in the running AI service.
        
        Returns:
            bool: True if config reloaded successfully
        """
        with self._service_lock:
            try:
                if self._service_instance and self._service_instance.is_alive():
                    # Reload timing configuration if method exists
                    if hasattr(self._service_instance, 'reload_timing_config'):
                        self._service_instance.reload_timing_config()
                        print("✅ AI service configuration reloaded")
                        return True
                    else:
                        print("⚠️ Service does not support config reload")
                        return False
                else:
                    print("⚠️ AI service is not running - cannot reload config")
                    return False
                    
            except Exception as e:
                print(f"❌ Failed to reload AI service config: {e}")
                return False
    
    def get_service_metrics(self) -> dict:
        """
        Get service performance metrics.
        
        Returns:
            dict: Metrics including decision count, error count, etc.
        """
        service = self.get_service()
        if not service:
            return {
                'decisions_made': 0,
                'errors_encountered': 0,
                'screenshots_processed': 0,
                'uptime_seconds': 0
            }
        
        # Extract metrics from service if available
        metrics = {
            'decisions_made': getattr(service, 'decision_count', 0),
            'errors_encountered': getattr(service, 'error_count', 0),
            'screenshots_processed': getattr(service, 'screenshot_count', 0),
            'uptime_seconds': (time.time() - getattr(service, 'start_time', time.time()))
        }
        
        return metrics


# Global service manager instance (singleton)
_service_manager = AIGameServiceManager()


def get_service_manager() -> AIGameServiceManager:
    """
    Get the global service manager instance.
    
    Returns:
        AIGameServiceManager: Singleton service manager instance
    """
    return _service_manager


# Backward compatibility functions - delegate to service manager
def get_ai_service() -> Optional[AIGameService]:
    """Get the current AI service instance (backward compatibility)"""
    return _service_manager.get_service()


def start_ai_service() -> bool:
    """Start the AI service (backward compatibility)"""
    return _service_manager.start_service()


def stop_ai_service() -> bool:
    """Stop the AI service (backward compatibility)"""
    return _service_manager.stop_service()


def is_ai_service_running() -> bool:
    """Check if AI service is running (backward compatibility)"""
    return _service_manager.is_service_running()


def reload_ai_service_timing_config() -> bool:
    """Reload timing configuration (backward compatibility)"""
    return _service_manager.reload_service_config()
"""
Django management command to stop AI GBA Player unified service.
"""

import sys
import time
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from dashboard.models import Process
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging

# Import unified service using relative path within Django project
try:
    from core.unified_game_service import get_unified_service, stop_unified_service
except ImportError as e:
    print(f"⚠️ Warning: Could not import unified service: {e}")
    def get_unified_service(): raise ImportError("Unified service not available")
    def stop_unified_service(): raise ImportError("Unified service not available")

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Stop AI GBA Player system processes'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'service_name',
            choices=['unified_service', 'all'],
            help='Name of the service to stop'
        )
    
    def handle(self, *args, **options):
        service_name = options['service_name']
        
        self.stdout.write(f'🛑 Stopping service: {service_name}')
        
        if service_name in ['unified_service', 'all']:
            self._stop_unified_service()
        else:
            raise CommandError(f'Unknown service: {service_name}')
    
    def _stop_unified_service(self):
        """Stop the unified service."""
        service_name = 'unified_service'
        
        try:
            process_obj = Process.objects.get(name=service_name)
        except Process.DoesNotExist:
            self.stdout.write(
                self.style.WARNING(f'⚠️ No service record found for {service_name}')
            )
            return
        
        # Update status to stopping
        process_obj.status = 'stopping'
        process_obj.save()
        
        # Broadcast status update
        self._broadcast_process_status(service_name, 'stopping')
        
        try:
            self.stdout.write(f'🛑 Stopping unified service...')
            
            # Stop the unified service
            stop_unified_service()
            
            # Service stopped successfully
            process_obj.status = 'stopped'
            process_obj.pid = None
            process_obj.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Stopped unified service successfully')
            )
            
            # Broadcast success
            self._broadcast_process_status(service_name, 'stopped')
            
        except Exception as e:
            process_obj.status = 'error'
            process_obj.last_error = str(e)[:500]
            process_obj.save()
            
            self.stdout.write(
                self.style.ERROR(f'❌ Exception stopping unified service: {e}')
            )
            
            # Broadcast error
            self._broadcast_process_status(service_name, 'error', error=str(e))
            raise CommandError(f'Failed to stop unified service: {e}')
    
    def _broadcast_process_status(self, process_name, status, error=None):
        """Broadcast process status update via Django Channels"""
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                message = {
                    'type': 'system_status',
                    'message': {
                        'system': {
                            'processes': {
                                process_name: {
                                    'status': status,
                                    'pid': None if status == 'stopped' else 'unknown',
                                    'last_error': error,
                                    'updated_at': time.time()
                                }
                            }
                        },
                        'timestamp': time.time()
                    }
                }
                
                async_to_sync(channel_layer.group_send)('dashboard', message)
                self.stdout.write(f'📡 Broadcasted {process_name} status: {status}')
                
        except Exception as e:
            self.stdout.write(f'⚠️ Failed to broadcast status: {e}')
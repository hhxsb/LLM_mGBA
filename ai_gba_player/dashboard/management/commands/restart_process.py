"""
Django management command to restart AI GBA Player unified service.
"""

import time
from django.core.management.base import BaseCommand
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Restart AI GBA Player unified service'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'service_name',
            choices=['unified_service', 'all'],
            help='Name of the service to restart'
        )
        parser.add_argument(
            '--config',
            type=str,
            default='config_emulator.json',
            help='Configuration file to use'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force restart even if service is not running'
        )
        parser.add_argument(
            '--wait',
            type=int,
            default=3,
            help='Wait time between stop and start (seconds)'
        )
    
    def handle(self, *args, **options):
        service_name = options['service_name']
        config_file = options['config']
        force = options['force']
        wait_time = options['wait']
        
        self.stdout.write(f'🔄 Restarting service: {service_name}')
        
        if service_name in ['unified_service', 'all']:
            self._restart_unified_service(config_file, force, wait_time)
        else:
            self.stdout.write(self.style.ERROR(f'❌ Unknown service: {service_name}'))
    
    def _restart_unified_service(self, config_file, force, wait_time):
        """Restart the unified service"""
        service_name = 'unified_service'
        
        # Stop the service first
        self.stdout.write('🛑 Stopping unified service...')
        try:
            call_command('stop_process', service_name, verbosity=1)
        except Exception as e:
            if not force:
                self.stdout.write(self.style.ERROR(f'❌ Failed to stop {service_name}: {e}'))
                return
            else:
                self.stdout.write(self.style.WARNING(f'⚠️ Service may not have stopped cleanly: {e}'))
        
        # Wait before starting
        if wait_time > 0:
            self.stdout.write(f'⏱️ Waiting {wait_time}s before restart...')
            time.sleep(wait_time)
        
        # Start the service
        self.stdout.write('🚀 Starting unified service...')
        try:
            call_command('start_process', service_name, config=config_file, force=True, verbosity=1)
            self.stdout.write(self.style.SUCCESS('✅ Unified service restarted successfully'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Failed to start unified service: {e}'))
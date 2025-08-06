"""
Django management command to restart Pokemon AI system processes.
"""

import time
from django.core.management.base import BaseCommand
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Restart Pokemon AI system processes'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'process_name',
            choices=['game_control', 'video_capture', 'knowledge_system', 'all'],
            help='Name of the process to restart'
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
            help='Force restart even if process is not running'
        )
        parser.add_argument(
            '--timeout',
            type=int,
            default=10,
            help='Timeout for graceful shutdown (seconds)'
        )
        parser.add_argument(
            '--wait',
            type=int,
            default=3,
            help='Wait time between stop and start (seconds)'
        )
    
    def handle(self, *args, **options):
        process_name = options['process_name']
        config_file = options['config']
        force = options['force']
        timeout = options['timeout']
        wait_time = options['wait']
        
        self.stdout.write(f'🔄 Restarting process: {process_name}')
        
        if process_name == 'all':
            self._restart_all_processes(config_file, force, timeout, wait_time)
        else:
            self._restart_single_process(process_name, config_file, force, timeout, wait_time)
    
    def _restart_all_processes(self, config_file, force, timeout, wait_time):
        """Restart all processes"""
        processes = ['video_capture', 'game_control', 'knowledge_system']
        
        # Stop all processes first
        self.stdout.write('🛑 Stopping all processes...')
        try:
            call_command('stop_process', 'all', force=force, timeout=timeout, verbosity=1)
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'⚠️ Some processes may not have stopped cleanly: {e}'))
        
        # Wait before starting
        if wait_time > 0:
            self.stdout.write(f'⏱️ Waiting {wait_time}s before restart...')
            time.sleep(wait_time)
        
        # Start all processes
        self.stdout.write('🚀 Starting all processes...')
        try:
            call_command('start_process', 'all', config=config_file, force=True, verbosity=1)
            self.stdout.write(self.style.SUCCESS('✅ All processes restarted successfully'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Failed to start some processes: {e}'))
    
    def _restart_single_process(self, process_name, config_file, force, timeout, wait_time):
        """Restart a single process"""
        
        # Stop the process
        self.stdout.write(f'🛑 Stopping {process_name}...')
        try:
            call_command('stop_process', process_name, force=force, timeout=timeout, verbosity=1)
        except Exception as e:
            if not force:
                self.stdout.write(self.style.ERROR(f'❌ Failed to stop {process_name}: {e}'))
                return
            else:
                self.stdout.write(self.style.WARNING(f'⚠️ Process may not have stopped cleanly: {e}'))
        
        # Wait before starting
        if wait_time > 0:
            self.stdout.write(f'⏱️ Waiting {wait_time}s before restart...')
            time.sleep(wait_time)
        
        # Start the process
        self.stdout.write(f'🚀 Starting {process_name}...')
        try:
            call_command('start_process', process_name, config=config_file, force=True, verbosity=1)
            self.stdout.write(self.style.SUCCESS(f'✅ Process {process_name} restarted successfully'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Failed to start {process_name}: {e}'))
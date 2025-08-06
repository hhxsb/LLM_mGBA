"""
Django management command to start Pokemon AI system processes.
"""

import subprocess
import sys
import time
import signal
import psutil
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from dashboard.models import Process
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Start Pokemon AI system processes'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'process_name',
            choices=['game_control', 'video_capture', 'knowledge_system', 'all'],
            help='Name of the process to start'
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
            help='Force start even if process is already running'
        )
        parser.add_argument(
            '--wait',
            type=int,
            default=5,
            help='Wait time between process starts (seconds)'
        )
    
    def handle(self, *args, **options):
        process_name = options['process_name']
        config_file = options['config']
        force = options['force']
        wait_time = options['wait']
        
        # Get project root directory
        project_root = Path(__file__).parent.parent.parent.parent.parent
        config_path = project_root / config_file
        
        if not config_path.exists():
            raise CommandError(f'Config file not found: {config_path}')
        
        self.stdout.write(f'🚀 Starting process: {process_name}')
        self.stdout.write(f'📁 Project root: {project_root}')
        self.stdout.write(f'⚙️ Config file: {config_path}')
        
        if process_name == 'all':
            self._start_all_processes(project_root, config_path, force, wait_time)
        else:
            self._start_single_process(process_name, project_root, config_path, force)
    
    def _start_all_processes(self, project_root, config_path, force, wait_time):
        """Start all processes in dependency order"""
        processes = ['video_capture', 'game_control']  # knowledge_system is integrated into game_control
        
        for process_name in processes:
            try:
                self._start_single_process(process_name, project_root, config_path, force)
                if wait_time > 0:
                    self.stdout.write(f'⏱️ Waiting {wait_time}s before starting next process...')
                    time.sleep(wait_time)
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Failed to start {process_name}: {e}')
                )
                # Continue with other processes
                continue
        
        self.stdout.write(self.style.SUCCESS('✅ All processes start sequence completed'))
    
    def _start_single_process(self, process_name, project_root, config_path, force):
        """Start a single process"""
        
        # Check if process is already running
        try:
            process_obj = Process.objects.get(name=process_name)
            if not force and process_obj.status == 'running' and process_obj.pid:
                if self._is_process_running(process_obj.pid):
                    self.stdout.write(
                        self.style.WARNING(f'⚠️ Process {process_name} is already running (PID: {process_obj.pid})')
                    )
                    return
        except Process.DoesNotExist:
            # Create process record if it doesn't exist
            process_obj = Process.objects.create(
                name=process_name,
                status='stopped'
            )
        
        # Update status to starting
        process_obj.status = 'starting'
        process_obj.last_error = ''
        process_obj.save()
        
        # Broadcast status update
        self._broadcast_process_status(process_name, 'starting')
        
        try:
            # Get process command and start it
            script_path, args = self._get_process_command(process_name, project_root, config_path)
            
            self.stdout.write(f'📜 Running: {script_path} {" ".join(args)}')
            
            # Start the process
            process = subprocess.Popen(
                [sys.executable, str(script_path)] + args,
                cwd=str(project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=None if sys.platform == "win32" else lambda: None
            )
            
            # Wait a moment to see if process starts successfully
            time.sleep(2)
            
            if process.poll() is None:
                # Process is running
                process_obj.pid = process.pid
                process_obj.status = 'running'
                process_obj.save()
                
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Started {process_name} (PID: {process.pid})')
                )
                
                # Broadcast success
                self._broadcast_process_status(process_name, 'running', process.pid)
                
            else:
                # Process failed to start
                stdout, stderr = process.communicate()
                error_msg = stderr.decode() if stderr else 'Process failed to start'
                
                process_obj.status = 'error'
                process_obj.last_error = error_msg[:500]  # Limit error message length
                process_obj.save()
                
                self.stdout.write(
                    self.style.ERROR(f'❌ Failed to start {process_name}: {error_msg}')
                )
                
                # Broadcast error
                self._broadcast_process_status(process_name, 'error', error=error_msg)
                
        except Exception as e:
            process_obj.status = 'error'
            process_obj.last_error = str(e)[:500]
            process_obj.save()
            
            self.stdout.write(
                self.style.ERROR(f'❌ Exception starting {process_name}: {e}')
            )
            
            # Broadcast error
            self._broadcast_process_status(process_name, 'error', error=str(e))
            raise CommandError(f'Failed to start {process_name}: {e}')
    
    def _get_process_command(self, process_name, project_root, config_path):
        """Get the command to run for each process"""
        commands = {
            'video_capture': (
                project_root / 'video_capture_process.py',
                ['--config', str(config_path)]
            ),
            'game_control': (
                project_root / 'game_control_process.py', 
                ['--config', str(config_path)]
            ),
            'knowledge_system': (
                project_root / 'core' / 'base_knowledge_system.py',  # Use base knowledge system
                []
            )
        }
        
        if process_name not in commands:
            raise CommandError(f'Unknown process: {process_name}')
        
        script_path, args = commands[process_name]
        
        if not script_path.exists():
            raise CommandError(f'Process script not found: {script_path}')
        
        return script_path, args
    
    def _is_process_running(self, pid):
        """Check if a process is running by PID"""
        try:
            process = psutil.Process(pid)
            return process.is_running()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
    
    def _broadcast_process_status(self, process_name, status, pid=None, error=None):
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
                                    'pid': pid,
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
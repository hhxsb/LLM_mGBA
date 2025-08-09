"""
Django management command to set up the Django dashboard system.
Runs migrations, creates initial data, and initializes the message bus bridge.
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from dashboard.models import Process
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Set up Django dashboard system with migrations and initial data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-migrations',
            action='store_true',
            help='Skip running migrations'
        )
        parser.add_argument(
            '--create-processes',
            action='store_true', 
            help='Create initial process records'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Setting up Django Dashboard...'))
        
        # Run migrations unless skipped
        if not options['skip_migrations']:
            self.stdout.write('📦 Running database migrations...')
            try:
                call_command('makemigrations', verbosity=0)
                call_command('migrate', verbosity=0)
                self.stdout.write(self.style.SUCCESS('✅ Database migrations completed'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Migration failed: {e}'))
                return
        
        # Create initial process records if requested
        if options['create_processes']:
            self.stdout.write('🔧 Creating initial process records...')
            self._create_initial_processes()
        
        # Initialize message bus bridge
        self.stdout.write('🌉 Initializing message bus bridge...')
        try:
            from core.django_message_bus import sync_initialize_django_message_bus
            sync_initialize_django_message_bus()
            self.stdout.write(self.style.SUCCESS('✅ Message bus bridge initialized'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Message bus initialization failed: {e}'))
        
        self.stdout.write(self.style.SUCCESS('🎉 Django Dashboard setup completed!'))
        self.stdout.write('')
        self.stdout.write('Next steps:')
        self.stdout.write('1. Start Django server: python manage.py runserver')
        self.stdout.write('2. Start Daphne for WebSocket support: daphne -b 0.0.0.0 -p 8000 ai_gba_player.asgi:application')
        self.stdout.write('3. Visit http://localhost:8000 to access the dashboard')
    
    def _create_initial_processes(self):
        """Create initial service records for AI GBA Player unified service"""
        services = [
            {
                'name': 'unified_service',
                'status': 'stopped',
                'port': None  # Unified service doesn't use a specific port
            }
        ]
        
        # Clean up old process records if they exist
        old_processes = ['game_control', 'video_capture', 'knowledge_system']
        removed_count = 0
        for old_process in old_processes:
            try:
                old_record = Process.objects.get(name=old_process)
                old_record.delete()
                removed_count += 1
                self.stdout.write(f'  🗑️ Removed old process record: {old_process}')
            except Process.DoesNotExist:
                pass
        
        if removed_count > 0:
            self.stdout.write(self.style.SUCCESS(f'✅ Cleaned up {removed_count} old process records'))
        
        created_count = 0
        for service_data in services:
            service, created = Process.objects.get_or_create(
                name=service_data['name'],
                defaults={
                    'status': service_data['status'],
                    'port': service_data['port']
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(f'  ✅ Created service: {service_data["name"]}')
            else:
                self.stdout.write(f'  ℹ️ Service already exists: {service_data["name"]}')
        
        self.stdout.write(self.style.SUCCESS(f'✅ Created {created_count} new service records'))
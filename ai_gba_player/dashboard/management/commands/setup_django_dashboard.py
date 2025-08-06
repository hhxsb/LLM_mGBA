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
        """Create initial process records for Pokemon AI system"""
        processes = [
            {
                'name': 'game_control',
                'status': 'stopped',
                'port': 8888
            },
            {
                'name': 'video_capture', 
                'status': 'stopped',
                'port': 8889
            },
            {
                'name': 'knowledge_system',
                'status': 'stopped',
                'port': None
            }
        ]
        
        created_count = 0
        for process_data in processes:
            process, created = Process.objects.get_or_create(
                name=process_data['name'],
                defaults={
                    'status': process_data['status'],
                    'port': process_data['port']
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(f'  ✅ Created process: {process_data["name"]}')
            else:
                self.stdout.write(f'  ℹ️ Process already exists: {process_data["name"]}')
        
        self.stdout.write(self.style.SUCCESS(f'✅ Created {created_count} new process records'))
# Pokemon AI Django Dashboard

A unified Django-based dashboard for managing and monitoring the Pokemon AI system. This replaces the previous React/FastAPI dual-stack architecture with a single, maintainable Django application.

## Features

### 🎮 Real-time Dashboard
- Live WebSocket streaming of game footage and AI responses
- Real-time process monitoring and system metrics
- Pokemon-themed responsive UI with modern glassmorphism design

### ⚙️ Process Management
- Start, stop, restart Pokemon AI system processes via web interface
- Command-line management tools for automation
- Real-time status broadcasting via WebSocket
- Process health monitoring with CPU/memory metrics

### 📊 Admin Panel
- Professional admin interface for system control
- Process logs and error tracking
- System information and performance metrics
- Quick action buttons for common operations

### 🌐 API Integration
- Complete REST API for all dashboard operations
- Django Channels WebSocket support
- Message bus integration with existing AI system

## Quick Start

### 1. Setup Django Dashboard
```bash
# Install dependencies
pip install django channels djangorestframework psutil

# Setup database and initial data
python manage.py setup_django_dashboard --create-processes

# Collect static files
python manage.py collectstatic --noinput
```

### 2. Start Django Server
```bash
# Development server
python manage.py runserver

# Production server (WebSocket support)
daphne -b 0.0.0.0 -p 8000 pokemon_ai_dashboard.asgi:application
```

### 3. Access Dashboard
- **Main Dashboard**: http://localhost:8000/
- **Admin Panel**: http://localhost:8000/admin-panel/
- **Django Admin**: http://localhost:8000/admin/
- **API Docs**: http://localhost:8000/api/

## Process Management

### Web Interface
1. Go to Admin Panel: http://localhost:8000/admin-panel/
2. Use the process control buttons to start/stop/restart processes
3. Monitor real-time status and system metrics

### Command Line Interface
```bash
# Start processes
python manage.py start_process video_capture --config config_emulator.json
python manage.py start_process game_control --config config_emulator.json
python manage.py start_process all --config config_emulator.json

# Stop processes
python manage.py stop_process video_capture
python manage.py stop_process all

# Restart processes  
python manage.py restart_process game_control
python manage.py restart_process all

# Check status
python manage.py status_process --detailed --update-db --broadcast
```

## Architecture

### Django Components
- **dashboard/**: Main dashboard app with WebSocket consumers
- **api/**: REST API endpoints for system control
- **core/**: Message bus integration and Django Channels bridge
- **templates/**: Responsive HTML templates with Pokemon theme
- **static/**: CSS, JavaScript, and assets

### Key Features
- **Unified Backend**: Single Django application replacing dual-stack
- **WebSocket Integration**: Real-time updates via Django Channels
- **Process Management**: Full lifecycle management of AI processes  
- **Message Bus Bridge**: Seamless integration with existing AI system
- **Database Persistence**: All chat messages and system state stored
- **Production Ready**: Professional admin interface and monitoring

### WebSocket Protocol
```json
{
  "type": "chat_message",
  "timestamp": 1672531200.0,
  "data": {
    "id": "msg_123",
    "type": "gif",
    "source": "video_capture", 
    "content": {
      "gif": {
        "data": "base64_gif_data",
        "metadata": {"frameCount": 30, "duration": 2.0}
      }
    }
  }
}
```

## Development

### Django Settings
- `DEBUG = True` for development
- WebSocket support via Django Channels
- Static files served from `dashboard/static/`
- SQLite database for persistence

### Custom Management Commands
- `setup_django_dashboard`: Initialize system
- `start_process`: Start AI processes
- `stop_process`: Stop AI processes  
- `restart_process`: Restart AI processes
- `status_process`: Check process status

### Message Bus Integration
The system bridges the existing Pokemon AI message bus with Django Channels:
```python
from core.django_message_bus import publish_gif_message, publish_response_message

# Publish messages from Django views
publish_response_message("AI is thinking...", source="django_dashboard")
```

## Migration from React/FastAPI

This Django system completely replaces the previous architecture:

### ✅ Replaced Components
- ❌ `dashboard/frontend/` (React app)
- ❌ `dashboard/backend/main.py` (FastAPI server)  
- ❌ Complex npm/Node.js build pipeline
- ❌ Dual-process frontend/backend coordination

### ✅ New Unified System
- ✅ Single Django application
- ✅ Server-side rendered templates
- ✅ Integrated WebSocket support
- ✅ Professional admin interface
- ✅ Command-line process management
- ✅ Production-ready deployment

## Production Deployment

```bash
# Install production dependencies
pip install daphne gunicorn

# Collect static files
python manage.py collectstatic --noinput

# Run with Daphne (WebSocket support)
daphne -b 0.0.0.0 -p 8000 pokemon_ai_dashboard.asgi:application

# Or run API-only with Gunicorn
gunicorn pokemon_ai_dashboard.wsgi:application
```

## Troubleshooting

### Common Issues
- **Port conflicts**: Django uses port 8000 by default
- **WebSocket connection**: Requires ASGI server (Daphne) for production
- **Static files**: Run `collectstatic` after changes
- **Process paths**: Ensure config file paths are correct

### Debug Mode
Enable detailed logging by setting `DEBUG = True` in Django settings.

---

🎮 **Pokemon AI Django Dashboard** - A complete, unified system for AI game control and monitoring!
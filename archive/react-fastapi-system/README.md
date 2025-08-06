# Archived React/FastAPI System

This directory contains the original React/FastAPI dual-stack architecture that has been replaced by the unified Django system.

## Archived Components

### Frontend (React)
- **Location**: `frontend/`
- **Technology**: React + TypeScript + Vite + Tailwind CSS
- **Components**: 
  - `AdminPanel.tsx` - Process management interface
  - `ChatInterface.tsx` - Real-time chat display
  - `StatusPanel.tsx` - System monitoring
- **Features**: Real-time WebSocket updates, responsive design

### Backend (FastAPI)
- **Location**: `backend/`
- **Technology**: FastAPI + WebSocket + Pydantic
- **Files**:
  - `main.py` - FastAPI server with WebSocket endpoints
  - `websocket_handler.py` - WebSocket message handling
  - `process_manager.py` - Process lifecycle management
  - `models.py` - Pydantic data models

## Migration to Django

These components have been **completely replaced** by the unified Django system located in:
```
pokemon_ai_dashboard/
├── dashboard/          # Django app (replaces both frontend & backend)
├── api/               # REST API (replaces FastAPI routes)
├── templates/         # HTML templates (replaces React components)
├── static/           # CSS/JS assets (replaces Vite build)
└── manage.py         # Django management (replaces npm scripts)
```

## Why Migrated?

### Problems with Dual-Stack
- ❌ Complex build pipeline (npm + Python)
- ❌ Two separate servers to manage
- ❌ Coordination issues between frontend/backend
- ❌ Different dependency management systems
- ❌ More complex deployment and maintenance

### Benefits of Django
- ✅ Single unified codebase
- ✅ Server-side rendering (faster initial load)
- ✅ Integrated WebSocket support via Django Channels
- ✅ Professional admin interface built-in
- ✅ Simplified deployment and maintenance
- ✅ Better process management integration

## Features Preserved

All functionality from the React/FastAPI system has been preserved:
- ✅ Real-time WebSocket communication
- ✅ Process management (start/stop/restart)
- ✅ System monitoring and metrics
- ✅ Pokemon-themed responsive UI
- ✅ Admin controls and error handling

## Archive Date
January 2025 - Replaced during Django migration

---

**Note**: These archived components are kept for reference only. The active system is now the Django-based dashboard in `pokemon_ai_dashboard/`.
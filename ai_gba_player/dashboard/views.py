from django.shortcuts import render
from django.http import JsonResponse
from .models import Process, ChatMessage, SystemLog
import time


def dashboard_view(request):
    """Main dashboard view"""
    context = {
        'title': 'AI GBA Player',
        'page': 'dashboard'
    }
    return render(request, 'dashboard/dashboard.html', context)


def admin_panel_view(request):
    """Admin panel view"""
    # Get current process status
    processes = Process.objects.all()
    recent_logs = SystemLog.objects.all()[:20]
    
    context = {
        'title': 'System Control - AI GBA Player',
        'page': 'admin',
        'processes': processes,
        'recent_logs': recent_logs
    }
    return render(request, 'dashboard/admin_panel.html', context)

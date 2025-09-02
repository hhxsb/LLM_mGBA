"""
URL configuration for ai_gba_player project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.views.decorators.csrf import csrf_exempt
from . import simple_views
from . import graphiti_views

urlpatterns = [
    # Django admin
    path('admin/', admin.site.urls),
    
    # Main application views
    path('', simple_views.dashboard_view, name='dashboard'),
    path('config/', simple_views.config_view, name='config'),
    
    # AI service API endpoints (all handled in simple_views.py)
    path('api/restart-service/', csrf_exempt(simple_views.restart_service), name='restart_service'),
    path('api/stop-service/', csrf_exempt(simple_views.stop_service), name='stop_service'),
    path('api/reset-llm-session/', csrf_exempt(simple_views.reset_llm_session), name='reset_llm_session'),
    path('api/launch-mgba-config/', csrf_exempt(simple_views.launch_mgba_config), name='launch_mgba_config'),
    path('api/save-rom-config/', csrf_exempt(simple_views.save_rom_config), name='save_rom_config'),
    path('api/save-ai-config/', csrf_exempt(simple_views.save_ai_config), name='save_ai_config'),
    path('api/chat-messages/', csrf_exempt(simple_views.get_chat_messages), name='get_chat_messages'),
    
    # Graphiti Memory System API endpoints
    path('api/graphiti/objectives/', csrf_exempt(graphiti_views.get_objectives), name='get_objectives'),
    path('api/graphiti/objectives/add/', csrf_exempt(graphiti_views.add_objective), name='add_objective'),
    path('api/graphiti/objectives/<str:objective_id>/complete/', csrf_exempt(graphiti_views.complete_objective), name='complete_objective'),
    path('api/graphiti/strategies/', csrf_exempt(graphiti_views.get_strategies), name='get_strategies'),
    path('api/graphiti/stats/', csrf_exempt(graphiti_views.get_memory_stats), name='get_memory_stats'),
    
    # Disabled: Legacy API app - superseded by simple_views
    # path('api/', include('api.urls')),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0] if settings.STATICFILES_DIRS else None)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

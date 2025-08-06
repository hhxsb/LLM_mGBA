from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.health_check, name='health_check'),
    path('status/', views.system_status, name='system_status'),
    path('processes/', views.process_status, name='process_status'),
    path('processes/<str:process_name>/start/', views.start_process, name='start_process'),
    path('processes/<str:process_name>/stop/', views.stop_process, name='stop_process'),
    path('processes/<str:process_name>/restart/', views.restart_process, name='restart_process'),
    path('messages/', views.recent_messages, name='recent_messages'),
    path('messages/clear/', views.clear_messages, name='clear_messages'),
    path('logs/', views.system_logs, name='system_logs'),
]
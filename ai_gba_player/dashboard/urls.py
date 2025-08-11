from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('admin-panel/', views.admin_panel_view, name='admin_panel'),
    
    # API endpoints
    path('api/restart-service/', views.restart_service, name='restart_service'),
    path('api/launch-mgba/', views.launch_mgba, name='launch_mgba'),
    path('api/launch-mgba-config/', views.launch_mgba_from_config, name='launch_mgba_config'),
    path('api/export-config/', views.export_config, name='export_config'),
    path('api/browse-files/', views.browse_files, name='browse_files'),
    path('api/common-paths/', views.get_common_paths, name='common_paths'),
    
    # File upload endpoints
    path('api/upload-file/', views.upload_file, name='upload_file'),
    path('api/create-rom-config/', views.create_rom_config, name='create_rom_config'),
    path('api/uploaded-files/', views.get_uploaded_files, name='get_uploaded_files'),
    
    
    # System configuration
    path('config/', views.config_view, name='config'),
]
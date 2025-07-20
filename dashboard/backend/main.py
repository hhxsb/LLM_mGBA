"""
Main FastAPI application for AI Pokemon Trainer Dashboard
"""
import asyncio
import json
import logging
import signal
import sys
import os
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from process_manager import ProcessManager
from websocket_handler import websocket_handler, connection_manager
from api import routes
from models import DashboardConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DashboardApp:
    """Main dashboard application"""
    
    def __init__(self, config_path: str = "config_emulator.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.dashboard_config = DashboardConfig(**self.config.get("dashboard", {}))
        
        # Initialize FastAPI app
        self.app = FastAPI(
            title="AI Pokemon Trainer Dashboard",
            description="Real-time dashboard for AI Pokemon Red gameplay",
            version="1.0.0"
        )
        
        # Initialize process manager  
        self.frontend_only = getattr(self, 'frontend_only', False)
        self.process_manager = ProcessManager(self.config, frontend_only=self.frontend_only)
        
        # Setup middleware
        self._setup_middleware()
        
        # Setup routes
        self._setup_routes()
        
        # Setup static files
        self._setup_static_files()
        
        # Setup signal handlers
        self._setup_signal_handlers()
        
        logger.info("🚀 AI Pokemon Trainer Dashboard initialized")
    
    def _load_config(self) -> dict:
        """Load configuration from file"""
        try:
            config_file = Path(self.config_path)
            if not config_file.exists():
                config_file = Path(__file__).parent.parent.parent / self.config_path
            
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            # Add dashboard defaults if not present
            if "dashboard" not in config:
                config["dashboard"] = {}
            
            return config
            
        except Exception as e:
            logger.error(f"❌ Error loading config: {e}")
            return {"dashboard": {}}
    
    def _setup_middleware(self):
        """Setup FastAPI middleware"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # In production, specify exact origins
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def _setup_routes(self):
        """Setup API routes and WebSocket endpoints"""
        # Inject process manager into routes
        routes.process_manager = self.process_manager
        
        # Initialize knowledge interface
        routes.initialize_knowledge_interface(self.config)
        
        # Include API routes
        self.app.include_router(routes.router)
        
        # WebSocket endpoint
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket_handler.handle_websocket(websocket)
        
        # Root endpoint - serve frontend
        @self.app.get("/")
        async def root():
            # Serve the frontend if available
            frontend_index = Path(__file__).parent.parent / "frontend" / "index.html"
            if frontend_index.exists():
                from fastapi.responses import FileResponse
                return FileResponse(str(frontend_index))
            else:
                return {
                    "service": "AI Pokemon Trainer Dashboard",
                    "status": "running",
                    "version": "1.0.0",
                    "websocket": "/ws",
                    "api": "/api/v1",
                    "frontend": "http://127.0.0.1:5173 (development)"
                }
    
    def _setup_static_files(self):
        """Setup static file serving"""
        try:
            # Serve static files (images, data, etc.)
            static_dir = Path(__file__).parent.parent.parent / "static"
            if static_dir.exists():
                self.app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
            
            # Serve frontend source files for development
            frontend_src = Path(__file__).parent.parent / "frontend" / "src"
            if frontend_src.exists():
                self.app.mount("/src", StaticFiles(directory=str(frontend_src)), name="frontend-src")
            
            # Serve frontend build (when available)
            frontend_build = Path(__file__).parent.parent / "frontend" / "build"
            if frontend_build.exists():
                self.app.mount("/app", StaticFiles(directory=str(frontend_build), html=True), name="frontend")
                
        except Exception as e:
            logger.warning(f"⚠️ Static files setup failed: {e}")
    
    def _setup_signal_handlers(self):
        """Setup graceful shutdown signal handlers"""
        def signal_handler(signum, frame):
            logger.info(f"🛑 Received signal {signum}, shutting down...")
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def startup(self):
        """Startup sequence"""
        logger.info("🚀 Starting AI Pokemon Trainer Dashboard...")
        
        try:
            # Auto-start all processes (including frontend)
            logger.info("🔄 Auto-starting all processes (including frontend)...")
            success = await self.process_manager.start_all_processes()
            if success:
                logger.info("✅ All processes started successfully")
                
                # Log frontend access URL
                if "frontend" in self.process_manager.processes:
                    logger.info("🌐 Frontend available at: http://localhost:5173")
                    logger.info("📊 Dashboard API at: http://127.0.0.1:3000/api/v1")
            else:
                logger.warning("⚠️ Some processes failed to start - dashboard will still work with reduced functionality")
            
            # Start background tasks
            asyncio.create_task(self._background_monitoring())
            
            logger.info("✅ Dashboard startup complete")
            
        except Exception as e:
            logger.error(f"❌ Error during startup: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown sequence"""
        logger.info("🛑 Shutting down AI Pokemon Trainer Dashboard...")
        
        try:
            # Stop all managed processes
            await self.process_manager.stop_all_processes()
            
            # Close WebSocket connections
            for connection in list(connection_manager.active_connections):
                try:
                    await connection.close()
                except:
                    pass
            
            logger.info("✅ Dashboard shutdown complete")
            
        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}")
    
    async def _background_monitoring(self):
        """Background task for monitoring and updates"""
        while True:
            try:
                # Send periodic status updates
                status = self.process_manager.get_system_status()
                status["websocket"] = {
                    "active_connections": connection_manager.get_connection_count(),
                    "uptime": connection_manager.get_uptime()
                }
                
                await connection_manager.broadcast_system_status(status)
                
                # Wait 10 seconds before next update
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"❌ Error in background monitoring: {e}")
                await asyncio.sleep(5)  # Shorter wait on error
    
    def run(self, host: str = "127.0.0.1", port: int = None):
        """Run the dashboard server"""
        if port is None:
            port = self.dashboard_config.port
        
        logger.info(f"🌐 Starting dashboard server at http://{host}:{port}")
        logger.info(f"📡 WebSocket available at ws://{host}:{port}/ws")
        logger.info(f"🔧 API available at http://{host}:{port}/api/v1")
        
        # Create event loop and run
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Run startup
            loop.run_until_complete(self.startup())
            
            # Run the server
            config = uvicorn.Config(
                app=self.app,
                host=host,
                port=port,
                log_level="info",
                loop="asyncio"
            )
            server = uvicorn.Server(config)
            loop.run_until_complete(server.serve())
            
        except KeyboardInterrupt:
            logger.info("🛑 Keyboard interrupt received")
        except Exception as e:
            logger.error(f"❌ Server error: {e}")
        finally:
            # Ensure cleanup
            loop.run_until_complete(self.shutdown())
            loop.close()

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='AI Pokemon Trainer Dashboard')
    parser.add_argument('--config', default='config_emulator.json', help='Configuration file path')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--port', type=int, help='Port to bind to (overrides config)')
    parser.add_argument('--frontend-only', action='store_true', help='Start only frontend and dashboard API (skip AI processes)')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Setup debug logging
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger('process_manager').setLevel(logging.DEBUG)
    
    try:
        app = DashboardApp(config_path=args.config)
        
        # Pass frontend-only flag to app
        if args.frontend_only:
            app.frontend_only = True
            logger.info("🎯 Frontend-only mode: AI processes will be skipped")
        
        app.run(host=args.host, port=args.port)
    except Exception as e:
        logger.error(f"❌ Failed to start dashboard: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
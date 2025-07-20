"""
Process Manager for AI Pokemon Trainer Dashboard
Handles lifecycle of video capture, game control, and knowledge system processes
"""
import asyncio
import subprocess
import psutil
import signal
import time
import json
import os
import sys
from typing import Dict, Optional, List
from pathlib import Path
import logging

sys.path.append(str(Path(__file__).parent))
from models import ProcessInfo, ProcessStatus

logger = logging.getLogger(__name__)

class ProcessManager:
    """Manages all AI Pokemon Trainer processes"""
    
    def __init__(self, config: Dict, frontend_only: bool = False):
        self.config = config
        self.frontend_only = frontend_only
        self.processes: Dict[str, ProcessInfo] = {}
        self.process_handles: Dict[str, subprocess.Popen] = {}
        self.start_time = time.time()
        self.project_root = Path(__file__).parent.parent.parent
        
        # Initialize process configurations
        self._init_process_configs()
    
    def _init_process_configs(self):
        """Initialize process configuration details"""
        logger.debug(f"🔧 Initializing process configs (frontend_only: {self.frontend_only})")
        
        # Check if npm is available
        frontend_dir = self.project_root / "dashboard" / "frontend"
        npm_available = self._check_npm_available(frontend_dir)
        
        self.process_configs = {
            "frontend": {
                "command": ["npm", "run", "dev"] if npm_available else None,
                "cwd": str(frontend_dir) if npm_available else None,
                "port": 5173,
                "required_for": [],
                "startup_delay": 3.0,
                "optional": True,
                "description": "Frontend development server"
            },
            "video_capture": {
                "command": self._get_video_capture_command(),
                "cwd": str(self.project_root),
                "port": self.config.get("dual_process_mode", {}).get("video_capture_port", 8889),
                "required_for": ["game_control"],
                "startup_delay": 2.0,
                "optional": True,
                "description": "Video capture process",
                "auto_restart": False
            },
            "game_control": {
                "command": self._get_game_control_command(),
                "cwd": str(self.project_root),
                "port": self.config.get("port", 8888),
                "required_for": [],
                "startup_delay": 3.0,
                "optional": True,
                "description": "Game control process",
                "auto_restart": False
            },
            "knowledge_system": {
                "command": self._get_knowledge_system_command(),
                "cwd": str(self.project_root),
                "port": None,
                "required_for": [],
                "startup_delay": 1.0,
                "optional": True,
                "description": "Knowledge system process",
                "auto_restart": False
            }
        }
        
        # Initialize process info
        for name, config in self.process_configs.items():
            logger.debug(f"🔍 Processing {name} (frontend_only: {self.frontend_only})")
            
            # Skip AI processes in frontend-only mode
            if self.frontend_only and name in ["video_capture", "game_control", "knowledge_system"]:
                logger.info(f"⏭️ Skipping {name} in frontend-only mode")
                continue
                
            if config.get("command"):  # Only add if command is available
                logger.debug(f"✅ Adding {name} to processes")
                self.processes[name] = ProcessInfo(
                    name=name,
                    status=ProcessStatus.STOPPED,
                    port=config.get("port")
                )
            else:
                logger.debug(f"⏭️ Skipping {name} - no command available")
    
    def _check_npm_available(self, frontend_dir: Path) -> bool:
        """Check if npm is available and frontend is set up"""
        try:
            # Check if npm is installed
            result = subprocess.run(["npm", "--version"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                logger.warning("⚠️ npm not found - frontend will not be available")
                return False
            
            # Check if package.json exists
            package_json = frontend_dir / "package.json"
            if not package_json.exists():
                logger.warning("⚠️ package.json not found - frontend will not be available")
                return False
            
            # Check if node_modules exists
            node_modules = frontend_dir / "node_modules"
            if not node_modules.exists():
                logger.info("📦 Installing frontend dependencies...")
                install_result = subprocess.run(["npm", "install"], 
                                               cwd=str(frontend_dir),
                                               capture_output=True, text=True, timeout=60)
                if install_result.returncode != 0:
                    logger.error("❌ Failed to install frontend dependencies")
                    return False
                logger.info("✅ Frontend dependencies installed")
            
            return True
            
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as e:
            logger.warning(f"⚠️ npm check failed: {e}")
            return False
    
    def _get_video_capture_command(self):
        """Get video capture command if file exists"""
        video_capture_file = self.project_root / "video_capture_process.py"
        if video_capture_file.exists():
            return [sys.executable, "video_capture_process.py", "--config", "config_emulator.json"]
        else:
            logger.warning("⚠️ video_capture_process.py not found - skipping")
            return None
    
    def _get_game_control_command(self):
        """Get game control command if file exists"""
        game_control_file = self.project_root / "game_control_process.py"
        if game_control_file.exists():
            return [sys.executable, "game_control_process.py", "--config", "config_emulator.json"]
        else:
            logger.warning("⚠️ game_control_process.py not found - skipping")
            return None
    
    def _get_knowledge_system_command(self):
        """Get knowledge system command if available"""
        # Check if Pokemon Red knowledge system exists (concrete implementation)
        pokemon_knowledge_file = self.project_root / "games" / "pokemon_red" / "knowledge_system.py"
        if pokemon_knowledge_file.exists():
            return [sys.executable, "-c", "from games.pokemon_red.knowledge_system import PokemonRedKnowledgeSystem; import time; ks = PokemonRedKnowledgeSystem('data/knowledge_graph.json'); time.sleep(3600)"]
        else:
            logger.warning("⚠️ Pokemon Red knowledge system not found - skipping")
            return None
    
    async def start_all_processes(self) -> bool:
        """Start all processes in the correct order"""
        logger.info("🚀 Starting all AI Pokemon Trainer processes...")
        
        try:
            # Start processes in dependency order
            startup_order = self._get_startup_order()
            
            for process_name in startup_order:
                # Check dependencies before starting
                if not self._check_dependencies(process_name):
                    logger.warning(f"⏭️ Skipping {process_name} - dependencies not met")
                    continue
                
                success = await self.start_process(process_name)
                config = self.process_configs[process_name]
                
                if not success:
                    if config.get("optional", False):
                        logger.warning(f"⚠️ Optional process {process_name} failed to start - continuing")
                        # If this process failed, mark dependent processes as skipped
                        self._mark_dependent_processes_skipped(process_name)
                    else:
                        logger.error(f"❌ Required process {process_name} failed to start, aborting startup")
                        await self.stop_all_processes()
                        return False
                else:
                    logger.info(f"✅ {process_name} started successfully")
                
                # Wait for startup delay
                await asyncio.sleep(config["startup_delay"])
            
            logger.info("✅ All processes started successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error during process startup: {e}")
            await self.stop_all_processes()
            return False
    
    async def start_process(self, process_name: str) -> bool:
        """Start a specific process"""
        if process_name not in self.process_configs:
            logger.error(f"❌ Unknown process: {process_name}")
            return False
        
        if self.processes[process_name].status == ProcessStatus.RUNNING:
            logger.info(f"⚠️ Process {process_name} is already running")
            return True
        
        config = self.process_configs[process_name]
        process_info = self.processes[process_name]
        
        try:
            logger.info(f"🔄 Starting {process_name}...")
            process_info.status = ProcessStatus.STARTING
            
            # Start the process
            process = subprocess.Popen(
                config["command"],
                cwd=config["cwd"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            self.process_handles[process_name] = process
            process_info.pid = process.pid
            process_info.status = ProcessStatus.RUNNING
            
            logger.info(f"✅ Started {process_name} (PID: {process.pid})")
            
            # Start monitoring task
            asyncio.create_task(self._monitor_process(process_name))
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start {process_name}: {e}")
            process_info.status = ProcessStatus.ERROR
            process_info.last_error = str(e)
            return False
    
    async def stop_process(self, process_name: str) -> bool:
        """Stop a specific process"""
        if process_name not in self.process_handles:
            return True
        
        try:
            process = self.process_handles[process_name]
            process_info = self.processes[process_name]
            
            logger.info(f"🛑 Stopping {process_name}...")
            
            # Try graceful shutdown first
            process.terminate()
            
            try:
                await asyncio.wait_for(asyncio.create_task(self._wait_for_process(process)), timeout=5.0)
            except asyncio.TimeoutError:
                # Force kill if graceful shutdown fails
                logger.warning(f"⚠️ Force killing {process_name}")
                process.kill()
                await asyncio.create_task(self._wait_for_process(process))
            
            del self.process_handles[process_name]
            process_info.status = ProcessStatus.STOPPED
            process_info.pid = None
            
            logger.info(f"✅ Stopped {process_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error stopping {process_name}: {e}")
            return False
    
    async def stop_all_processes(self):
        """Stop all processes in reverse dependency order"""
        logger.info("🛑 Stopping all processes...")
        
        # Stop in reverse order
        startup_order = self._get_startup_order()
        for process_name in reversed(startup_order):
            await self.stop_process(process_name)
        
        logger.info("✅ All processes stopped")
    
    async def restart_process(self, process_name: str) -> bool:
        """Restart a specific process"""
        logger.info(f"🔄 Restarting {process_name}...")
        
        await self.stop_process(process_name)
        await asyncio.sleep(1.0)  # Brief pause
        success = await self.start_process(process_name)
        
        if success:
            self.processes[process_name].restart_count += 1
        
        return success
    
    def get_system_status(self) -> Dict:
        """Get current system status"""
        return {
            "processes": {name: info.dict() for name, info in self.processes.items()},
            "uptime": time.time() - self.start_time,
            "memory_usage": self._get_memory_usage()
        }
    
    def _get_startup_order(self) -> List[str]:
        """Determine the correct startup order based on dependencies"""
        # Frontend first, then AI processes in dependency order
        # frontend -> video_capture -> game_control -> knowledge_system
        startup_order = []
        
        # Add frontend first if available
        if "frontend" in self.processes:
            startup_order.append("frontend")
        
        # Add AI processes in dependency order (video_capture must start before game_control)
        ai_processes = ["video_capture", "game_control", "knowledge_system"]
        for process in ai_processes:
            if process in self.processes:
                startup_order.append(process)
        
        return startup_order
    
    def _check_dependencies(self, process_name: str) -> bool:
        """Check if all dependencies for a process are running"""
        config = self.process_configs.get(process_name, {})
        required_for = config.get("required_for", [])
        
        # Special dependency rules
        if process_name == "game_control":
            # game_control requires video_capture to be running
            video_capture_info = self.processes.get("video_capture")
            if not video_capture_info or video_capture_info.status.value != "running":
                logger.debug(f"🔍 game_control dependency check: video_capture not running")
                return False
        
        return True
    
    def _mark_dependent_processes_skipped(self, failed_process: str):
        """Mark processes that depend on the failed process as skipped"""
        if failed_process == "video_capture":
            # If video_capture fails, game_control will also fail
            logger.info(f"📋 Marking game_control as skipped due to video_capture failure")
    
    async def _monitor_process(self, process_name: str):
        """Monitor a process and handle failures"""
        process = self.process_handles.get(process_name)
        process_info = self.processes[process_name]
        
        if not process:
            return
        
        try:
            while process.poll() is None:
                await asyncio.sleep(1.0)
                
                # Update uptime
                if process_info.status == ProcessStatus.RUNNING:
                    # Check if process is actually responsive
                    if not self._check_process_health(process_name):
                        logger.warning(f"⚠️ Process {process_name} appears unresponsive")
            
            # Process has exited
            exit_code = process.poll()
            if exit_code != 0:
                # Capture stderr/stdout for debugging
                try:
                    stdout, stderr = process.communicate(timeout=1)
                    error_details = f"Exit code: {exit_code}"
                    if stderr.strip():
                        error_details += f"\nSTDERR: {stderr.strip()}"
                    if stdout.strip():
                        error_details += f"\nSTDOUT: {stdout.strip()}"
                    
                    logger.error(f"❌ Process {process_name} failed:\n{error_details}")
                    process_info.last_error = error_details
                except subprocess.TimeoutExpired:
                    logger.error(f"❌ Process {process_name} exited with code {exit_code} (output timeout)")
                    process_info.last_error = f"Process exited with code {exit_code}"
                
                process_info.status = ProcessStatus.ERROR
                
                # Check if this process should auto-restart
                config = self.process_configs.get(process_name, {})
                should_restart = config.get("auto_restart", True) and self.config.get("dashboard", {}).get("auto_restart", True)
                
                if config.get("optional", False) and not should_restart:
                    logger.warning(f"⚠️ Optional process {process_name} failed - not restarting")
                elif should_restart:
                    logger.info(f"🔄 Auto-restarting {process_name}...")
                    await asyncio.sleep(2.0)
                    await self.restart_process(process_name)
                else:
                    logger.info(f"⚠️ Process {process_name} failed - auto-restart disabled")
            else:
                process_info.status = ProcessStatus.STOPPED
                
        except Exception as e:
            logger.error(f"❌ Error monitoring {process_name}: {e}")
            process_info.status = ProcessStatus.ERROR
            process_info.last_error = str(e)
    
    def _check_process_health(self, process_name: str) -> bool:
        """Check if a process is healthy and responsive"""
        try:
            process_info = self.processes[process_name]
            if not process_info.pid:
                return False
            
            # Check if PID exists
            try:
                psutil.Process(process_info.pid)
                return True
            except psutil.NoSuchProcess:
                return False
                
        except Exception:
            return False
    
    def _get_memory_usage(self) -> Dict[str, float]:
        """Get memory usage for all processes"""
        memory_usage = {}
        
        for name, info in self.processes.items():
            if info.pid:
                try:
                    process = psutil.Process(info.pid)
                    memory_usage[name] = process.memory_info().rss / 1024 / 1024  # MB
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    memory_usage[name] = 0.0
            else:
                memory_usage[name] = 0.0
        
        return memory_usage
    
    async def _wait_for_process(self, process: subprocess.Popen):
        """Wait for a process to terminate"""
        while process.poll() is None:
            await asyncio.sleep(0.1)
    
    def __del__(self):
        """Cleanup on destruction"""
        # Note: This is synchronous cleanup, async cleanup should be done explicitly
        for process in self.process_handles.values():
            try:
                process.terminate()
            except:
                pass
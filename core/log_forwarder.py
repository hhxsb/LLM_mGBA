"""
Real-time log forwarding system for WebSocket streaming.
Monitors individual process log files and forwards logs to WebSocket clients.
"""

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, Optional, Callable, Set
import tempfile
from collections import deque

from .logging_config import get_logger

logger = get_logger("core.log_forwarder")

class LogForwarder:
    """Real-time log forwarder that monitors process log files and streams to WebSocket"""
    
    def __init__(self, websocket_broadcast_func: Callable):
        self.websocket_broadcast = websocket_broadcast_func
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        self.file_positions: Dict[str, int] = {}
        self.rate_limiter: Dict[str, deque] = {}
        self.max_logs_per_second = 100  # Rate limiting per process
        self.running = False
        
        # Get log directory
        self.log_dir = Path(tempfile.gettempdir()) / 'pokemon_ai_logs'
        self.log_dir.mkdir(exist_ok=True)
        
        logger.info("🔄 Log forwarder initialized")
    
    async def start_monitoring(self, process_names: Set[str]):
        """Start monitoring log files for specified processes"""
        self.running = True
        
        for process_name in process_names:
            if process_name not in self.monitoring_tasks:
                await self.start_process_monitoring(process_name)
        
        logger.info(f"📡 Started monitoring {len(process_names)} process log files")
    
    async def start_process_monitoring(self, process_name: str):
        """Start monitoring a specific process log file"""
        log_file = self.log_dir / f"{process_name}.log"
        
        # Initialize rate limiter
        self.rate_limiter[process_name] = deque()
        
        # Start monitoring task
        task = asyncio.create_task(self._monitor_log_file(process_name, log_file))
        self.monitoring_tasks[process_name] = task
        
        logger.debug(f"🔍 Started monitoring {log_file}")
    
    async def stop_monitoring(self):
        """Stop all log monitoring"""
        self.running = False
        
        # Cancel all monitoring tasks
        for process_name, task in list(self.monitoring_tasks.items()):
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        self.monitoring_tasks.clear()
        self.file_positions.clear()
        self.rate_limiter.clear()
        
        logger.info("🛑 Stopped all log monitoring")
    
    async def _monitor_log_file(self, process_name: str, log_file: Path):
        """Monitor a single log file for changes and forward new lines"""
        try:
            while self.running:
                try:
                    if log_file.exists():
                        await self._read_new_lines(process_name, log_file)
                    else:
                        # File doesn't exist yet, wait for it
                        await asyncio.sleep(1.0)
                        continue
                    
                    # Check for new content every 0.5 seconds
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"❌ Error monitoring {log_file}: {e}")
                    await asyncio.sleep(5.0)  # Longer wait on error
                    
        except asyncio.CancelledError:
            logger.debug(f"🛑 Monitoring cancelled for {process_name}")
        except Exception as e:
            logger.error(f"❌ Fatal error monitoring {process_name}: {e}")
    
    async def _read_new_lines(self, process_name: str, log_file: Path):
        """Read new lines from log file and forward to WebSocket"""
        try:
            current_size = log_file.stat().st_size
            last_position = self.file_positions.get(process_name, 0)
            
            # If file was truncated (overwritten), reset position
            if current_size < last_position:
                last_position = 0
                logger.debug(f"🔄 Log file {log_file} was reset, starting from beginning")
            
            # If no new content, return
            if current_size <= last_position:
                return
            
            # Read new content
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(last_position)
                new_content = f.read(current_size - last_position)
                self.file_positions[process_name] = current_size
            
            # Process new lines
            if new_content.strip():
                lines = new_content.strip().split('\n')
                for line in lines:
                    if line.strip():
                        await self._forward_log_line(process_name, line.strip())
                        
        except FileNotFoundError:
            # File was deleted, reset position
            self.file_positions[process_name] = 0
        except Exception as e:
            logger.error(f"❌ Error reading {log_file}: {e}")
    
    async def _forward_log_line(self, process_name: str, line: str):
        """Parse and forward a log line to WebSocket"""
        try:
            # Rate limiting check
            if not self._check_rate_limit(process_name):
                return
            
            # Parse log line (format: timestamp - [PID:name] - logger - level - message)
            log_entry = self._parse_log_line(line)
            if not log_entry:
                return
            
            # Create WebSocket message
            message = {
                "type": "log_stream",
                "data": {
                    "source": process_name,
                    "level": log_entry.get("level", "INFO"),
                    "message": log_entry.get("message", line),
                    "timestamp": time.time(),
                    "process_id": process_name
                }
            }
            
            # Forward to WebSocket (fire-and-forget)
            try:
                await self.websocket_broadcast(message)
            except Exception as e:
                logger.debug(f"⚠️ WebSocket broadcast failed: {e}")
                
        except Exception as e:
            logger.error(f"❌ Error forwarding log line: {e}")
    
    def _parse_log_line(self, line: str) -> Optional[Dict]:
        """Parse a log line into components"""
        try:
            # Expected format: "HH:MM:SS - [PID:name] - logger - LEVEL - message"
            parts = line.split(' - ', 4)
            if len(parts) >= 4:
                level_part = parts[3]
                message_part = parts[4] if len(parts) > 4 else ""
                
                return {
                    "level": level_part,
                    "message": message_part
                }
            else:
                # Fallback for malformed lines
                return {
                    "level": "INFO",
                    "message": line
                }
                
        except Exception:
            # Fallback for any parsing errors
            return {
                "level": "INFO", 
                "message": line
            }
    
    def _check_rate_limit(self, process_name: str) -> bool:
        """Check if we should forward this log (rate limiting)"""
        now = time.time()
        rate_queue = self.rate_limiter[process_name]
        
        # Remove old entries (older than 1 second)
        while rate_queue and rate_queue[0] < now - 1.0:
            rate_queue.popleft()
        
        # Check if we're under the limit
        if len(rate_queue) >= self.max_logs_per_second:
            return False
        
        # Add current timestamp
        rate_queue.append(now)
        return True

# Global instance (will be initialized by main dashboard)
log_forwarder: Optional[LogForwarder] = None

def initialize_log_forwarder(websocket_broadcast_func: Callable) -> LogForwarder:
    """Initialize the global log forwarder instance"""
    global log_forwarder
    log_forwarder = LogForwarder(websocket_broadcast_func)
    return log_forwarder

def get_log_forwarder() -> Optional[LogForwarder]:
    """Get the global log forwarder instance"""
    return log_forwarder
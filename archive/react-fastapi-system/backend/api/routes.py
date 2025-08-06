"""
REST API routes for the AI Pokemon Trainer Dashboard
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List, Optional
import time
import logging
import sys
import asyncio
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from models import ProcessInfo, SystemStatus, DashboardConfig
from process_manager import ProcessManager
from websocket_handler import connection_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")

# This will be injected by the main app
process_manager: Optional[ProcessManager] = None

def get_process_manager() -> ProcessManager:
    """Dependency to get process manager instance"""
    if process_manager is None:
        raise HTTPException(status_code=503, detail="Process manager not initialized")
    return process_manager

@router.get("/status")
async def get_system_status() -> Dict:
    """Get current system status"""
    try:
        if process_manager:
            process_status = process_manager.get_system_status()
        else:
            process_status = {"processes": {}, "uptime": 0, "memory_usage": {}}
        
        return {
            "system": process_status,
            "websocket": {
                "active_connections": connection_manager.get_connection_count(),
                "uptime": connection_manager.get_uptime(),
                "message_count": len(connection_manager.message_history)
            },
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"❌ Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/processes")
async def get_processes(pm: ProcessManager = Depends(get_process_manager)) -> Dict[str, ProcessInfo]:
    """Get status of all processes"""
    try:
        status = pm.get_system_status()
        return status["processes"]
    except Exception as e:
        logger.error(f"❌ Error getting processes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/processes/{process_name}/start")
async def start_process(process_name: str, pm: ProcessManager = Depends(get_process_manager)) -> Dict:
    """Start a specific process"""
    try:
        success = await pm.start_process(process_name)
        if success:
            return {"message": f"Process {process_name} started successfully", "success": True}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to start process {process_name}")
    except Exception as e:
        logger.error(f"❌ Error starting process {process_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/processes/{process_name}/stop")
async def stop_process(process_name: str, pm: ProcessManager = Depends(get_process_manager)) -> Dict:
    """Stop a specific process"""
    try:
        success = await pm.stop_process(process_name)
        if success:
            return {"message": f"Process {process_name} stopped successfully", "success": True}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to stop process {process_name}")
    except Exception as e:
        logger.error(f"❌ Error stopping process {process_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/processes/{process_name}/restart")
async def restart_process(process_name: str, pm: ProcessManager = Depends(get_process_manager)) -> Dict:
    """Restart a specific process"""
    try:
        success = await pm.restart_process(process_name)
        if success:
            return {"message": f"Process {process_name} restarted successfully", "success": True}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to restart process {process_name}")
    except Exception as e:
        logger.error(f"❌ Error restarting process {process_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/processes/start-all")
async def start_all_processes(pm: ProcessManager = Depends(get_process_manager)) -> Dict:
    """Start all processes"""
    try:
        success = await pm.start_all_processes()
        if success:
            return {"message": "All processes started successfully", "success": True}
        else:
            raise HTTPException(status_code=500, detail="Failed to start all processes")
    except Exception as e:
        logger.error(f"❌ Error starting all processes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/processes/stop-all")
async def stop_all_processes(pm: ProcessManager = Depends(get_process_manager)) -> Dict:
    """Stop all processes"""
    try:
        await pm.stop_all_processes()
        return {"message": "All processes stopped successfully", "success": True}
    except Exception as e:
        logger.error(f"❌ Error stopping all processes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/chat/history")
async def get_chat_history(limit: int = 50) -> Dict:
    """Get recent chat message history"""
    try:
        # Get recent messages from connection manager
        recent_messages = list(connection_manager.message_history)
        if limit > 0:
            recent_messages = recent_messages[-limit:]
        
        return {
            "messages": recent_messages,
            "total_count": len(connection_manager.message_history),
            "limit": limit
        }
    except Exception as e:
        logger.error(f"❌ Error getting chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat/clear")
async def clear_chat_history() -> Dict:
    """Clear chat message history"""
    try:
        connection_manager.message_history.clear()
        connection_manager.message_sequence = 0
        
        # Notify all clients
        await connection_manager.broadcast_message({
            "type": "chat_cleared",
            "data": {"message": "Chat history cleared", "timestamp": time.time()}
        })
        
        return {"message": "Chat history cleared successfully", "success": True}
    except Exception as e:
        logger.error(f"❌ Error clearing chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/config")
async def get_dashboard_config() -> Dict:
    """Get current dashboard configuration"""
    try:
        # This would normally come from a config file or database
        config = DashboardConfig()
        return config.dict()
    except Exception as e:
        logger.error(f"❌ Error getting dashboard config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check() -> Dict:
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "ai-pokemon-trainer-dashboard"
    }

@router.get("/processes/{process_name}/logs")
async def get_process_logs(process_name: str, limit: int = 100) -> Dict:
    """Get logs for a specific process"""
    try:
        if process_manager and hasattr(process_manager, 'processes') and process_name in process_manager.processes:
            process_info = process_manager.processes[process_name]
            process_handle = process_manager.process_handles.get(process_name)
            
            logs = []
            if process_handle:
                # Try to get recent output if available
                try:
                    # This is a simplified approach - in production you'd want proper log aggregation
                    if process_info.last_error:
                        logs.append({
                            "timestamp": time.time(),
                            "level": "ERROR",
                            "message": process_info.last_error
                        })
                    
                    logs.append({
                        "timestamp": time.time(),
                        "level": "INFO", 
                        "message": f"Process {process_name} status: {process_info.status.value}"
                    })
                    
                except Exception as e:
                    logs.append({
                        "timestamp": time.time(),
                        "level": "ERROR",
                        "message": f"Failed to get logs: {e}"
                    })
            
            # Limit results
            logs = logs[-limit:] if limit > 0 else logs
            
            return {
                "process_name": process_name,
                "logs": logs,
                "total_lines": len(logs),
                "limit": limit
            }
        else:
            raise HTTPException(status_code=404, detail=f"Process {process_name} not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting process logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/processes/{process_name}/restart-force")
async def force_restart_process(process_name: str, pm: ProcessManager = Depends(get_process_manager)) -> Dict:
    """Force restart a process (manual admin action)"""
    try:
        if process_name not in pm.processes:
            raise HTTPException(status_code=404, detail=f"Process {process_name} not found")
        
        logger.info(f"🔄 Admin manual restart of {process_name}")
        
        # Stop first
        await pm.stop_process(process_name)
        await asyncio.sleep(1.0)
        
        # Then start
        success = await pm.start_process(process_name)
        
        if success:
            return {
                "message": f"Process {process_name} manually restarted",
                "success": True,
                "action": "manual_restart"
            }
        else:
            return {
                "message": f"Failed to restart process {process_name}",
                "success": False,
                "action": "manual_restart"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error restarting process {process_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Knowledge system integration
knowledge_interface = None

def initialize_knowledge_interface(config: Dict):
    """Initialize knowledge interface with config"""
    global knowledge_interface
    try:
        from knowledge_integration import DashboardKnowledgeInterface
        knowledge_interface = DashboardKnowledgeInterface(config)
        logger.info("✅ Knowledge interface initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize knowledge interface: {e}")

@router.get("/knowledge/tasks")
async def get_knowledge_tasks() -> Dict:
    """Get current knowledge tasks"""
    try:
        if knowledge_interface and knowledge_interface.is_available():
            tasks = knowledge_interface.get_current_tasks()
            return {
                "tasks": tasks,
                "total": len(tasks),
                "knowledge_available": True
            }
        else:
            # Return mock data when knowledge system unavailable
            mock_tasks = [
                {
                    "id": "placeholder_1",
                    "title": "Knowledge System Integration",
                    "description": "Connecting to real knowledge system...",
                    "priority": "high",
                    "status": "in_progress",
                    "category": "system"
                }
            ]
            return {
                "tasks": mock_tasks,
                "total": len(mock_tasks),
                "knowledge_available": False,
                "message": "Knowledge system not available"
            }
    except Exception as e:
        logger.error(f"❌ Error getting knowledge tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/knowledge/summary")
async def get_knowledge_summary() -> Dict:
    """Get knowledge system summary"""
    try:
        if knowledge_interface and knowledge_interface.is_available():
            summary = knowledge_interface.get_knowledge_summary()
            return {
                "summary": summary,
                "knowledge_available": True
            }
        else:
            return {
                "summary": {
                    "character": {"name": "TRAINER", "game_phase": "connecting"},
                    "tasks": {"total": 0, "completed": 0, "active": 0, "pending": 0},
                    "message": "Knowledge system initializing..."
                },
                "knowledge_available": False
            }
    except Exception as e:
        logger.error(f"❌ Error getting knowledge summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/knowledge/tutorial")
async def get_tutorial_progress() -> Dict:
    """Get tutorial progress information"""
    try:
        if knowledge_interface and knowledge_interface.is_available():
            progress = knowledge_interface.get_tutorial_progress()
            return progress
        else:
            return {
                "completed_steps": [],
                "current_phase": "connecting",
                "guidance": "Connecting to knowledge system...",
                "progress_summary": "Initializing...",
                "next_steps": "Please wait",
                "total_completed": 0,
                "knowledge_available": False
            }
    except Exception as e:
        logger.error(f"❌ Error getting tutorial progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/knowledge/npcs")
async def get_npc_interactions(limit: int = 10) -> Dict:
    """Get recent NPC interactions"""
    try:
        if knowledge_interface and knowledge_interface.is_available():
            interactions = knowledge_interface.get_npc_interactions(limit)
            return {
                "interactions": interactions,
                "total": len(interactions),
                "knowledge_available": True
            }
        else:
            return {
                "interactions": [],
                "total": 0,
                "knowledge_available": False,
                "message": "Knowledge system not available"
            }
    except Exception as e:
        logger.error(f"❌ Error getting NPC interactions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/knowledge/tasks")
async def create_knowledge_task(task_data: Dict) -> Dict:
    """Create a new knowledge task"""
    try:
        title = task_data.get("title", "")
        description = task_data.get("description", "")
        priority = task_data.get("priority", "medium")
        category = task_data.get("category", "general")
        
        if not title:
            raise HTTPException(status_code=400, detail="Task title is required")
        
        if knowledge_interface and knowledge_interface.is_available():
            success = knowledge_interface.add_task(title, description, priority, category)
            if success:
                return {"message": "Task created successfully", "success": True}
            else:
                raise HTTPException(status_code=500, detail="Failed to create task")
        else:
            return {
                "message": "Knowledge system not available - task not saved",
                "success": False,
                "knowledge_available": False
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error creating knowledge task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/knowledge/tasks/{task_id}")
async def update_knowledge_task(task_id: str, update_data: Dict) -> Dict:
    """Update a knowledge task"""
    try:
        new_status = update_data.get("status")
        if not new_status:
            raise HTTPException(status_code=400, detail="Status is required for task update")
        
        if knowledge_interface and knowledge_interface.is_available():
            success = knowledge_interface.update_task_status(task_id, new_status)
            if success:
                return {"message": "Task updated successfully", "success": True}
            else:
                raise HTTPException(status_code=404, detail="Task not found or update failed")
        else:
            return {
                "message": "Knowledge system not available - update not saved",
                "success": False,
                "knowledge_available": False
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating knowledge task: {e}")
        raise HTTPException(status_code=500, detail=str(e))
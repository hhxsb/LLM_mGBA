"""
Graphiti Memory System API endpoints for AI GBA Player.
Provides independent API for viewing and managing Graphiti memory system.
"""

import json
import sys
from pathlib import Path
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import Graphiti memory system
try:
    from ai_gba_player.core.graphiti_memory import GraphitiMemorySystem, SimpleMemorySystem
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False


def get_memory_system():
    """Get the appropriate memory system instance"""
    if not MEMORY_AVAILABLE:
        return None
    
    try:
        # Try to get Graphiti memory system first
        return GraphitiMemorySystem()
    except Exception:
        # Fallback to simple memory system
        return SimpleMemorySystem()


def get_objectives(_request):
    """Get current objectives from Graphiti memory system"""
    if not MEMORY_AVAILABLE:
        return JsonResponse({
            'success': False,
            'message': 'Memory system not available'
        })
    
    try:
        memory_system = get_memory_system()
        if not memory_system:
            return JsonResponse({
                'success': False,
                'message': 'Failed to initialize memory system'
            })
        
        objectives = memory_system.get_current_objectives(max_count=10)
        
        # Convert objectives to JSON-serializable format
        objectives_data = []
        for obj in objectives:
            obj_data = {
                'id': obj.id,
                'description': obj.description,
                'priority': obj.priority,
                'category': obj.category,
                'discovered_at': obj.discovered_at,
                'location_discovered': obj.location_discovered,
                'completed': obj.completed_at is not None,
                'completed_at': obj.completed_at
            }
            objectives_data.append(obj_data)
        
        return JsonResponse({
            'success': True,
            'objectives': objectives_data,
            'count': len(objectives_data)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error getting objectives: {str(e)}'
        })


@csrf_exempt
def add_objective(request):
    """Add a new objective to Graphiti memory system"""
    if not MEMORY_AVAILABLE:
        return JsonResponse({
            'success': False,
            'message': 'Memory system not available'
        })
    
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'message': 'POST method required'
        })
    
    try:
        data = json.loads(request.body)
        description = data.get('description', '').strip()
        priority = int(data.get('priority', 5))
        category = data.get('category', 'manual')
        
        if not description:
            return JsonResponse({
                'success': False,
                'message': 'Description is required'
            })
        
        memory_system = get_memory_system()
        if not memory_system:
            return JsonResponse({
                'success': False,
                'message': 'Failed to initialize memory system'
            })
        
        objective_id = memory_system.discover_objective(
            description=description,
            location="Manual entry via frontend",
            category=category,
            priority=priority
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Objective added: {description}',
            'objective_id': objective_id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error adding objective: {str(e)}'
        })


@csrf_exempt
def complete_objective(request, objective_id):
    """Mark an objective as completed"""
    if not MEMORY_AVAILABLE:
        return JsonResponse({
            'success': False,
            'message': 'Memory system not available'
        })
    
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'message': 'POST method required'
        })
    
    try:
        memory_system = get_memory_system()
        if not memory_system:
            return JsonResponse({
                'success': False,
                'message': 'Failed to initialize memory system'
            })
        
        success = memory_system.complete_objective(
            objective_id=objective_id,
            location="Manual completion via frontend"
        )
        
        if success:
            return JsonResponse({
                'success': True,
                'message': f'Objective {objective_id} marked as completed'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': f'Objective {objective_id} not found or already completed'
            })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error completing objective: {str(e)}'
        })


def get_strategies(_request):
    """Get learned strategies from Graphiti memory system"""
    if not MEMORY_AVAILABLE:
        return JsonResponse({
            'success': False,
            'message': 'Memory system not available'
        })
    
    try:
        memory_system = get_memory_system()
        if not memory_system:
            return JsonResponse({
                'success': False,
                'message': 'Failed to initialize memory system'
            })
        
        # Get strategies for common situations
        situations = ["battle", "navigation", "dialogue", "menu"]
        all_strategies = []
        
        for situation in situations:
            strategies = memory_system.get_relevant_strategies(situation, min_success_rate=0.3)
            for strategy in strategies:
                strategy_data = {
                    'id': strategy.id,
                    'situation': strategy.situation_description,
                    'buttons': strategy.buttons,
                    'success_rate': round(strategy.success_rate * 100, 1),
                    'times_used': strategy.times_used,
                    'last_used': strategy.last_used
                }
                all_strategies.append(strategy_data)
        
        # Remove duplicates and sort by success rate
        unique_strategies = {s['id']: s for s in all_strategies}.values()
        sorted_strategies = sorted(unique_strategies, key=lambda x: x['success_rate'], reverse=True)
        
        return JsonResponse({
            'success': True,
            'strategies': sorted_strategies,
            'count': len(sorted_strategies)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error getting strategies: {str(e)}'
        })


def get_memory_stats(_request):
    """Get memory system statistics"""
    if not MEMORY_AVAILABLE:
        return JsonResponse({
            'success': False,
            'message': 'Memory system not available'
        })
    
    try:
        memory_system = get_memory_system()
        if not memory_system:
            return JsonResponse({
                'success': False,
                'message': 'Failed to initialize memory system'
            })
        
        # Get basic counts
        objectives = memory_system.get_current_objectives(max_count=100)
        active_objectives = [obj for obj in objectives if obj.completed_at is None]
        completed_objectives = [obj for obj in objectives if obj.completed_at is not None]
        
        strategies = memory_system.get_relevant_strategies("", min_success_rate=0.0)  # Get all strategies
        
        # Calculate average success rate
        avg_success_rate = 0
        if strategies:
            avg_success_rate = sum(s.success_rate for s in strategies) / len(strategies)
        
        stats = {
            'total_objectives': len(objectives),
            'active_objectives': len(active_objectives),
            'completed_objectives': len(completed_objectives),
            'learned_strategies': len(strategies),
            'avg_strategy_success': round(avg_success_rate * 100, 1),
            'memory_system_type': 'Graphiti' if hasattr(memory_system, 'graphiti') else 'Simple'
        }
        
        return JsonResponse({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error getting memory stats: {str(e)}'
        })
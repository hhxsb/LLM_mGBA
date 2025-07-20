#!/usr/bin/env python3
"""
Web-based Knowledge Manager - Interactive CRUD interface
"""
import json
import os
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import urllib.parse
import cgi
from knowledge_system import KnowledgeGraph, Goal

class KnowledgeWebManager(BaseHTTPRequestHandler):
    knowledge_file = "data/knowledge_graph.json"
    
    def parse_post_data(self):
        """Parse POST data properly handling both form-data and url-encoded"""
        content_type = self.headers.get('Content-Type', '')
        content_length = int(self.headers.get('Content-Length', 0))
        
        if content_length == 0:
            return {}
        
        post_data = self.rfile.read(content_length)
        
        if 'multipart/form-data' in content_type:
            # Handle multipart form data
            import io
            environ = {
                'REQUEST_METHOD': 'POST',
                'CONTENT_TYPE': content_type,
                'CONTENT_LENGTH': str(content_length)
            }
            fp = io.BytesIO(post_data)
            form = cgi.FieldStorage(fp=fp, environ=environ)
            
            data = {}
            for field in form.list:
                data[field.name] = field.value
            return data
        else:
            # Handle URL-encoded data
            data_str = post_data.decode('utf-8')
            return {k: v[0] if len(v) == 1 else v for k, v in urllib.parse.parse_qs(data_str).items()}
    
    def do_GET(self):
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/':
            self.serve_manager_dashboard()
        elif parsed_path.path == '/api/goals':
            self.serve_goals_api()
        elif parsed_path.path == '/api/locations':
            self.serve_locations_api()
        elif parsed_path.path == '/api/patterns':
            self.serve_patterns_api()
        else:
            self.send_error(404)
    
    def do_POST(self):
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/api/goals':
            self.handle_goal_post()
        elif parsed_path.path == '/api/goals/update':
            self.handle_goal_update()
        elif parsed_path.path == '/api/goals/delete':
            self.handle_goal_delete()
        elif parsed_path.path == '/api/patterns/solution':
            self.handle_pattern_solution()
        elif parsed_path.path == '/api/memory/reset':
            self.handle_memory_reset()
        else:
            self.send_error(404)
    
    def serve_manager_dashboard(self):
        """Serve the management dashboard HTML"""
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>Pokemon AI Knowledge Manager</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .header { background: #34495e; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .section { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .section h2 { margin-top: 0; color: #2c3e50; border-bottom: 2px solid #ecf0f1; padding-bottom: 10px; }
        .goal-item { margin: 10px 0; padding: 15px; background: #f8f9fa; border-left: 4px solid #3498db; border-radius: 4px; }
        .goal-active { border-left-color: #27ae60; }
        .goal-completed { border-left-color: #95a5a6; opacity: 0.7; }
        .goal-failed { border-left-color: #e74c3c; }
        .goal-blocked { border-left-color: #f39c12; }
        .btn { padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; margin: 2px; font-size: 14px; }
        .btn-primary { background: #3498db; color: white; }
        .btn-success { background: #27ae60; color: white; }
        .btn-warning { background: #f39c12; color: white; }
        .btn-danger { background: #e74c3c; color: white; }
        .btn:hover { opacity: 0.9; }
        .form-group { margin: 10px 0; }
        .form-control { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
        .form-inline { display: flex; gap: 10px; align-items: center; margin: 10px 0; }
        .form-inline .form-control { width: auto; flex: 1; }
        .priority { background: #e74c3c; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.8em; }
        .timestamp { color: #7f8c8d; font-size: 0.9em; }
        .goal-actions { margin-top: 10px; }
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; }
        .modal-content { background: white; margin: 5% auto; padding: 20px; border-radius: 8px; width: 90%; max-width: 500px; }
        .close { float: right; font-size: 28px; font-weight: bold; cursor: pointer; }
        .close:hover { color: #e74c3c; }
        .pattern-item { margin: 10px 0; padding: 15px; background: #fff5f5; border-left: 4px solid #e74c3c; border-radius: 4px; }
        .tabs { display: flex; margin-bottom: 20px; }
        .tab { padding: 10px 20px; background: #ecf0f1; border: none; cursor: pointer; border-radius: 4px 4px 0 0; margin-right: 5px; }
        .tab.active { background: #3498db; color: white; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .location-item { margin: 10px 0; padding: 15px; background: #f0f8ff; border-left: 4px solid #3498db; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🛠️ Pokemon AI Knowledge Manager</h1>
        <p>Create, update, and manage the AI's goals and knowledge</p>
    </div>

    <div class="tabs">
        <button class="tab active" onclick="showTab('goals')">🎯 Goals</button>
        <button class="tab" onclick="showTab('locations')">📍 Locations</button>
        <button class="tab" onclick="showTab('patterns')">❌ Patterns</button>
        <button class="tab" onclick="showTab('memory')">🧠 Memory</button>
    </div>

    <!-- Goals Tab -->
    <div id="goals" class="tab-content active">
        <div class="section">
            <h2>Create New Goal</h2>
            <div class="form-inline">
                <input type="text" id="newGoalDesc" class="form-control" placeholder="Goal description" />
                <select id="newGoalPriority" class="form-control" style="width: 120px;">
                    <option value="10">10 (Highest)</option>
                    <option value="9">9 (Very High)</option>
                    <option value="8">8 (High)</option>
                    <option value="7">7</option>
                    <option value="6">6</option>
                    <option value="5" selected>5 (Medium)</option>
                    <option value="4">4</option>
                    <option value="3">3</option>
                    <option value="2">2 (Low)</option>
                    <option value="1">1 (Lowest)</option>
                </select>
                <select id="newGoalType" class="form-control" style="width: 120px;">
                    <option value="manual">Manual</option>
                    <option value="main">Main Quest</option>
                    <option value="sub">Sub Quest</option>
                    <option value="exploration">Exploration</option>
                    <option value="collection">Collection</option>
                </select>
                <button class="btn btn-primary" onclick="createGoal()">➕ Create Goal</button>
            </div>
        </div>

        <div class="section">
            <h2>Current Goals</h2>
            <div style="margin-bottom: 15px;">
                <button class="btn btn-primary" onclick="loadGoals()">🔄 Refresh</button>
                <button class="btn btn-success" onclick="loadGoals('active')">Active Only</button>
                <button class="btn btn-warning" onclick="loadGoals('completed')">Completed</button>
            </div>
            <div id="goalsList">Loading goals...</div>
        </div>
    </div>

    <!-- Locations Tab -->
    <div id="locations" class="tab-content">
        <div class="section">
            <h2>Discovered Locations</h2>
            <button class="btn btn-primary" onclick="loadLocations()">🔄 Refresh</button>
            <div id="locationsList">Loading locations...</div>
        </div>
    </div>

    <!-- Patterns Tab -->
    <div id="patterns" class="tab-content">
        <div class="section">
            <h2>Learned Failure Patterns</h2>
            <button class="btn btn-primary" onclick="loadPatterns()">🔄 Refresh</button>
            <div id="patternsList">Loading patterns...</div>
        </div>
    </div>

    <!-- Memory Management Tab -->
    <div id="memory" class="tab-content">
        <div class="section">
            <h2>Memory Management</h2>
            <p>Manage the AI's memory and knowledge base. Use with caution!</p>
            
            <div style="background: #fff5f5; border: 1px solid #e74c3c; border-radius: 4px; padding: 15px; margin: 20px 0;">
                <h3 style="color: #e74c3c; margin-top: 0;">⚠️ Danger Zone</h3>
                <p><strong>Reset All Memory:</strong> This will permanently delete all goals, locations, failure patterns, NPC interactions, and action history. The AI will start with a completely fresh memory.</p>
                <p style="margin-bottom: 15px;"><strong>This action cannot be undone!</strong></p>
                <button class="btn btn-danger" onclick="confirmMemoryReset()">🧹 Reset All Memory</button>
            </div>
            
            <div style="background: #f0f8ff; border: 1px solid #3498db; border-radius: 4px; padding: 15px; margin: 20px 0;">
                <h3 style="color: #3498db; margin-top: 0;">📊 Memory Statistics</h3>
                <div id="memoryStats">Loading memory statistics...</div>
                <button class="btn btn-primary" onclick="loadMemoryStats()">🔄 Refresh Stats</button>
            </div>
        </div>
    </div>

    <!-- Reset Confirmation Modal -->
    <div id="resetModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeResetModal()">&times;</span>
            <h2 style="color: #e74c3c;">⚠️ Confirm Memory Reset</h2>
            <p><strong>Are you absolutely sure you want to reset all memory?</strong></p>
            <p>This will permanently delete:</p>
            <ul>
                <li>All goals and progress</li>
                <li>All discovered locations</li>
                <li>All learned failure patterns</li>
                <li>All NPC interactions</li>
                <li>Complete action history</li>
            </ul>
            <p style="color: #e74c3c;"><strong>This action cannot be undone!</strong></p>
            <div class="form-group">
                <label>Type "RESET" to confirm:</label>
                <input type="text" id="resetConfirmation" class="form-control" placeholder="Type RESET here" />
            </div>
            <div class="form-group">
                <button class="btn btn-danger" onclick="performMemoryReset()">🧹 Yes, Reset Everything</button>
                <button class="btn" onclick="closeResetModal()">❌ Cancel</button>
            </div>
        </div>
    </div>

    <!-- Edit Goal Modal -->
    <div id="editModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeModal()">&times;</span>
            <h2>Edit Goal</h2>
            <div class="form-group">
                <label>Description:</label>
                <input type="text" id="editGoalDesc" class="form-control" />
            </div>
            <div class="form-group">
                <label>Priority (1-10):</label>
                <select id="editGoalPriority" class="form-control">
                    <option value="10">10 (Highest)</option>
                    <option value="9">9 (Very High)</option>
                    <option value="8">8 (High)</option>
                    <option value="7">7</option>
                    <option value="6">6</option>
                    <option value="5">5 (Medium)</option>
                    <option value="4">4</option>
                    <option value="3">3</option>
                    <option value="2">2 (Low)</option>
                    <option value="1">1 (Lowest)</option>
                </select>
            </div>
            <div class="form-group">
                <label>Status:</label>
                <select id="editGoalStatus" class="form-control">
                    <option value="active">Active</option>
                    <option value="completed">Completed</option>
                    <option value="blocked">Blocked</option>
                    <option value="failed">Failed</option>
                </select>
            </div>
            <div class="form-group">
                <button class="btn btn-primary" onclick="updateGoal()">💾 Save Changes</button>
                <button class="btn" onclick="closeModal()">❌ Cancel</button>
            </div>
        </div>
    </div>

    <script>
        let currentEditGoalId = null;
        let currentGoalsData = [];


        function createGoal() {
            const description = document.getElementById('newGoalDesc').value.trim();
            const priority = document.getElementById('newGoalPriority').value;
            const type = document.getElementById('newGoalType').value;
            
            if (!description) {
                alert('Please enter a goal description');
                return;
            }
            
            console.log('DEBUG: Creating goal with:', {description, priority, type});
            
            const data = new FormData();
            data.append('action', 'create');
            data.append('description', description);
            data.append('priority', priority);
            data.append('type', type);
            
            fetch('/api/goals', {
                method: 'POST',
                body: data
            })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    document.getElementById('newGoalDesc').value = '';
                    loadGoals();
                } else {
                    alert('Error creating goal: ' + result.error);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error creating goal');
            });
        }

        function loadGoals(statusFilter = null) {
            let url = '/api/goals';
            if (statusFilter) {
                url += '?status=' + statusFilter;
            }
            
            fetch(url)
                .then(response => response.json())
                .then(goals => {
                    displayGoals(goals);
                })
                .catch(error => {
                    console.error('Error loading goals:', error);
                    document.getElementById('goalsList').innerHTML = '<div style="color: red;">Error loading goals</div>';
                });
        }

        function displayGoals(goals) {
            currentGoalsData = goals; // Store for index-based access
            const container = document.getElementById('goalsList');
            
            if (goals.length === 0) {
                container.innerHTML = '<div style="text-align: center; color: #7f8c8d; padding: 20px;">No goals found</div>';
                return;
            }
            
            container.innerHTML = goals.map((goal, index) => `
                <div class="goal-item goal-${goal.status}" data-goal-id="${goal.id}">
                    <div style="display: flex; justify-content: between; align-items: flex-start;">
                        <div style="flex: 1;">
                            <strong>${goal.description}</strong>
                            <span class="priority">Priority: ${goal.priority}</span>
                            <div class="timestamp">
                                Status: ${goal.status} | Type: ${goal.type} | 
                                Created: ${new Date(goal.created_time * 1000).toLocaleDateString()}
                                ${goal.location_id ? ` | Location: Map ${goal.location_id}` : ''}
                            </div>
                        </div>
                    </div>
                    <div class="goal-actions">
                        <button class="btn btn-primary" onclick="editGoalByIndex(${index})">✏️ Edit</button>
                        ${goal.status !== 'completed' ? `<button class="btn btn-success" onclick="completeGoalByIndex(${index})">✅ Complete</button>` : ''}
                        ${goal.status !== 'active' ? `<button class="btn btn-warning" onclick="activateGoalByIndex(${index})">🔄 Activate</button>` : ''}
                        <button class="btn btn-danger" onclick="deleteGoalByIndex(${index})">🗑️ Delete</button>
                    </div>
                </div>
            `).join('');
        }

        function editGoal(id, description, priority, status) {
            currentEditGoalId = id;
            document.getElementById('editGoalDesc').value = description;
            document.getElementById('editGoalPriority').value = priority;
            document.getElementById('editGoalStatus').value = status;
            document.getElementById('editModal').style.display = 'block';
        }

        function closeModal() {
            document.getElementById('editModal').style.display = 'none';
            currentEditGoalId = null;
        }

        function updateGoal() {
            if (!currentEditGoalId) return;
            
            const data = new FormData();
            data.append('goal_id', currentEditGoalId);
            data.append('description', document.getElementById('editGoalDesc').value);
            data.append('priority', document.getElementById('editGoalPriority').value);
            data.append('status', document.getElementById('editGoalStatus').value);
            
            fetch('/api/goals/update', {
                method: 'POST',
                body: data
            })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    closeModal();
                    loadGoals();
                } else {
                    alert('Error updating goal: ' + result.error);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error updating goal');
            });
        }

        function completeGoal(goalId) {
            updateGoalStatus(goalId, 'completed');
        }

        function activateGoal(goalId) {
            updateGoalStatus(goalId, 'active');
        }

        function updateGoalStatus(goalId, status) {
            const data = new FormData();
            data.append('goal_id', goalId);
            data.append('status', status);
            
            fetch('/api/goals/update', {
                method: 'POST',
                body: data
            })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    loadGoals();
                } else {
                    alert('Error updating goal: ' + result.error);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error updating goal');
            });
        }

        function editGoalByIndex(index) {
            const goal = currentGoalsData[index];
            if (goal) {
                editGoal(goal.id, goal.description, goal.priority, goal.status);
            }
        }

        function completeGoalByIndex(index) {
            const goal = currentGoalsData[index];
            if (goal) {
                completeGoal(goal.id);
            }
        }

        function activateGoalByIndex(index) {
            const goal = currentGoalsData[index];
            if (goal) {
                activateGoal(goal.id);
            }
        }

        function deleteGoalByIndex(index) {
            console.log('DEBUG: deleteGoalByIndex called with index:', index);
            console.log('DEBUG: currentGoalsData:', currentGoalsData);
            
            const goal = currentGoalsData[index];
            console.log('DEBUG: goal at index', index, ':', goal);
            
            if (goal && goal.id) {
                console.log('DEBUG: Calling deleteGoal with ID:', goal.id);
                deleteGoal(goal.id, goal.description);
            } else {
                console.error('DEBUG: No goal found at index', index, 'or goal has no ID');
                alert('Error: Goal not found or missing ID');
            }
        }

        function deleteGoal(goalId, description) {
            console.log('DEBUG: deleteGoal called with goalId:', goalId);
            
            const data = new FormData();
            data.append('goal_id', goalId);
            
            console.log('DEBUG: FormData created, goal_id =', data.get('goal_id'));
            
            fetch('/api/goals/delete', {
                method: 'POST',
                body: data
            })
            .then(response => response.json())
            .then(result => {
                console.log('DEBUG: Delete response:', result);
                if (result.success) {
                    loadGoals();
                } else {
                    alert('Error deleting goal: ' + result.error);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error deleting goal');
            });
        }

        function loadLocations() {
            fetch('/api/locations')
                .then(response => response.json())
                .then(locations => {
                    displayLocations(locations);
                })
                .catch(error => {
                    console.error('Error loading locations:', error);
                    document.getElementById('locationsList').innerHTML = '<div style="color: red;">Error loading locations</div>';
                });
        }

        function displayLocations(locations) {
            const container = document.getElementById('locationsList');
            
            if (locations.length === 0) {
                container.innerHTML = '<div style="text-align: center; color: #7f8c8d; padding: 20px;">No locations discovered yet</div>';
                return;
            }
            
            container.innerHTML = locations.map(loc => `
                <div class="location-item">
                    <strong>${loc.name}</strong> (Map ID: ${loc.map_id})
                    <div class="timestamp">
                        Position: (${loc.coordinates[0]}, ${loc.coordinates[1]}) | 
                        Visited: ${loc.visited_count} times
                        ${loc.last_visited ? ` | Last: ${new Date(loc.last_visited * 1000).toLocaleString()}` : ''}
                    </div>
                </div>
            `).join('');
        }

        function loadPatterns() {
            fetch('/api/patterns')
                .then(response => response.json())
                .then(patterns => {
                    displayPatterns(patterns);
                })
                .catch(error => {
                    console.error('Error loading patterns:', error);
                    document.getElementById('patternsList').innerHTML = '<div style="color: red;">Error loading patterns</div>';
                });
        }

        function displayPatterns(patterns) {
            const container = document.getElementById('patternsList');
            
            if (patterns.length === 0) {
                container.innerHTML = '<div style="text-align: center; color: #7f8c8d; padding: 20px;">No failure patterns learned yet</div>';
                return;
            }
            
            container.innerHTML = patterns.map(pattern => `
                <div class="pattern-item">
                    <strong>Situation:</strong> ${pattern.situation}<br>
                    <strong>Failed actions:</strong> ${pattern.failed_actions.join(', ')}<br>
                    ${pattern.successful_alternative ? 
                        `<strong>✅ Alternative:</strong> ${pattern.successful_alternative}<br>` : 
                        `<div style="margin-top: 10px;">
                            <input type="text" placeholder="Enter successful solution..." id="solution_${pattern.pattern_id}" style="width: 70%; padding: 5px;">
                            <button class="btn btn-success" onclick="addSolution('${pattern.pattern_id}')">💡 Add Solution</button>
                        </div>`
                    }
                    <div class="timestamp">
                        Occurred: ${pattern.occurrence_count} times | 
                        Last: ${new Date(pattern.last_seen * 1000).toLocaleString()}
                    </div>
                </div>
            `).join('');
        }

        function addSolution(patternId) {
            const solution = document.getElementById(`solution_${patternId}`).value.trim();
            if (!solution) {
                alert('Please enter a solution');
                return;
            }
            
            const data = new FormData();
            data.append('pattern_id', patternId);
            data.append('solution', solution);
            
            fetch('/api/patterns/solution', {
                method: 'POST',
                body: data
            })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    loadPatterns();
                } else {
                    alert('Error adding solution: ' + result.error);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error adding solution');
            });
        }

        // Memory Management Functions
        function loadMemoryStats() {
            Promise.all([
                fetch('/api/goals').then(r => r.json()),
                fetch('/api/locations').then(r => r.json()),
                fetch('/api/patterns').then(r => r.json())
            ])
            .then(([goals, locations, patterns]) => {
                const stats = `
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px;">
                        <div style="text-align: center; padding: 10px; background: #f8f9fa; border-radius: 4px;">
                            <strong style="font-size: 24px; color: #3498db;">${goals.length}</strong><br>
                            <span style="color: #7f8c8d;">Goals</span>
                        </div>
                        <div style="text-align: center; padding: 10px; background: #f8f9fa; border-radius: 4px;">
                            <strong style="font-size: 24px; color: #3498db;">${locations.length}</strong><br>
                            <span style="color: #7f8c8d;">Locations</span>
                        </div>
                        <div style="text-align: center; padding: 10px; background: #f8f9fa; border-radius: 4px;">
                            <strong style="font-size: 24px; color: #3498db;">${patterns.length}</strong><br>
                            <span style="color: #7f8c8d;">Patterns</span>
                        </div>
                    </div>
                `;
                document.getElementById('memoryStats').innerHTML = stats;
            })
            .catch(error => {
                console.error('Error loading memory stats:', error);
                document.getElementById('memoryStats').innerHTML = '<div style="color: red;">Error loading statistics</div>';
            });
        }

        function confirmMemoryReset() {
            document.getElementById('resetModal').style.display = 'block';
            document.getElementById('resetConfirmation').value = '';
        }

        function closeResetModal() {
            document.getElementById('resetModal').style.display = 'none';
            document.getElementById('resetConfirmation').value = '';
        }

        function performMemoryReset() {
            const confirmation = document.getElementById('resetConfirmation').value;
            if (confirmation !== 'RESET') {
                alert('You must type "RESET" to confirm the memory reset');
                return;
            }

            const data = new FormData();
            data.append('confirm', 'RESET');
            
            fetch('/api/memory/reset', {
                method: 'POST',
                body: data
            })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    alert('Memory reset completed successfully!');
                    closeResetModal();
                    // Refresh all tabs
                    loadGoals();
                    loadLocations();
                    loadPatterns();
                    loadMemoryStats();
                } else {
                    alert('Error resetting memory: ' + result.error);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error resetting memory');
            });
        }

        // Update showTab function to load memory stats
        function showTab(tabName) {
            // Hide all tab contents
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            
            // Remove active class from all tabs
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Show selected tab content
            document.getElementById(tabName).classList.add('active');
            
            // Add active class to clicked tab
            event.target.classList.add('active');
            
            // Load content for the tab
            if (tabName === 'goals') {
                loadGoals();
            } else if (tabName === 'locations') {
                loadLocations();
            } else if (tabName === 'patterns') {
                loadPatterns();
            } else if (tabName === 'memory') {
                loadMemoryStats();
            }
        }

        // Initial load
        loadGoals();
    </script>
</body>
</html>
        """
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())
    
    def serve_goals_api(self):
        """Serve goals API"""
        try:
            # Ensure knowledge file exists
            if not os.path.exists(self.knowledge_file):
                os.makedirs(os.path.dirname(self.knowledge_file), exist_ok=True)
            
            kg = KnowledgeGraph(self.knowledge_file)
            query = parse_qs(urlparse(self.path).query)
            status_filter = query.get('status', [None])[0]
            
            goals = list(kg.goals.values())
            if status_filter:
                goals = [g for g in goals if g.status == status_filter]
            
            # Sort by priority (high to low) then by creation time
            goals.sort(key=lambda x: (-x.priority, x.created_time))
            
            # Convert to dict for JSON serialization
            goals_data = []
            for goal in goals:
                goals_data.append({
                    'id': goal.id,
                    'description': goal.description,
                    'type': goal.type,
                    'status': goal.status,
                    'priority': goal.priority,
                    'location_id': goal.location_id,
                    'created_time': goal.created_time,
                    'completed_time': goal.completed_time,
                    'attempts_count': len(goal.attempts)
                })
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(goals_data).encode())
            
        except Exception as e:
            self.send_error(500, str(e))
    
    def serve_locations_api(self):
        """Serve locations API"""
        try:
            kg = KnowledgeGraph(self.knowledge_file)
            locations = sorted(kg.locations.values(), 
                             key=lambda x: x.visited_count, reverse=True)
            
            locations_data = []
            for loc in locations:
                locations_data.append({
                    'map_id': loc.map_id,
                    'name': loc.name,
                    'coordinates': loc.coordinates,
                    'visited_count': loc.visited_count,
                    'last_visited': loc.last_visited,
                    'npcs_count': len(loc.npcs),
                    'items_count': len(loc.items)
                })
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(locations_data).encode())
            
        except Exception as e:
            self.send_error(500, str(e))
    
    def serve_patterns_api(self):
        """Serve failure patterns API"""
        try:
            kg = KnowledgeGraph(self.knowledge_file)
            patterns = sorted(kg.failure_patterns.values(),
                            key=lambda x: x.occurrence_count, reverse=True)
            
            patterns_data = []
            for pattern in patterns:
                patterns_data.append({
                    'pattern_id': pattern.pattern_id,
                    'situation': pattern.situation,
                    'failed_actions': pattern.failed_actions,
                    'successful_alternative': pattern.successful_alternative,
                    'occurrence_count': pattern.occurrence_count,
                    'last_seen': pattern.last_seen
                })
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(patterns_data).encode())
            
        except Exception as e:
            self.send_error(500, str(e))
    
    def handle_goal_post(self):
        """Handle goal creation"""
        try:
            data = self.parse_post_data()
            
            action = data.get('action', '')
            
            if action == 'create':
                description = data.get('description', '')
                priority = int(data.get('priority', '5'))
                goal_type = data.get('type', 'manual')
                
                if not description:
                    raise ValueError("Description is required")
                
                kg = KnowledgeGraph(self.knowledge_file)
                goal_id = f"manual_{int(time.time())}"
                
                goal = Goal(
                    id=goal_id,
                    description=description,
                    type=goal_type,
                    status="active",
                    priority=priority
                )
                
                kg.goals[goal_id] = goal
                kg.save_knowledge()
                
                response = {"success": True, "goal_id": goal_id}
            else:
                response = {"success": False, "error": "Unknown action"}
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            response = {"success": False, "error": str(e)}
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
    
    def handle_goal_update(self):
        """Handle goal updates"""
        try:
            data = self.parse_post_data()
            
            goal_id = data.get('goal_id', '')
            if not goal_id:
                raise ValueError("Goal ID is required")
            
            kg = KnowledgeGraph(self.knowledge_file)
            if goal_id not in kg.goals:
                raise ValueError("Goal not found")
            
            goal = kg.goals[goal_id]
            
            # Update fields if provided
            if 'description' in data:
                goal.description = data['description']
            if 'priority' in data:
                goal.priority = int(data['priority'])
            if 'status' in data:
                goal.status = data['status']
                if goal.status == 'completed' and not goal.completed_time:
                    goal.completed_time = time.time()
            
            kg.save_knowledge()
            
            response = {"success": True}
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            response = {"success": False, "error": str(e)}
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
    
    def handle_goal_delete(self):
        """Handle goal deletion"""
        try:
            data = self.parse_post_data()
            
            goal_id = data.get('goal_id', '')
            
            if not goal_id:
                raise ValueError("Goal ID is required")
            
            kg = KnowledgeGraph(self.knowledge_file)
            
            if goal_id not in kg.goals:
                raise ValueError(f"Goal not found: {goal_id}")
            
            del kg.goals[goal_id]
            kg.save_knowledge()
            
            response = {"success": True}
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            response = {"success": False, "error": str(e)}
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
    
    def handle_pattern_solution(self):
        """Handle adding solutions to failure patterns"""
        try:
            data = self.parse_post_data()
            
            pattern_id = data.get('pattern_id', '')
            solution = data.get('solution', '')
            
            if not pattern_id or not solution:
                raise ValueError("Pattern ID and solution are required")
            
            kg = KnowledgeGraph(self.knowledge_file)
            if pattern_id not in kg.failure_patterns:
                raise ValueError("Pattern not found")
            
            pattern = kg.failure_patterns[pattern_id]
            pattern.successful_alternative = solution
            kg.save_knowledge()
            
            response = {"success": True}
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            response = {"success": False, "error": str(e)}
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
    
    def handle_memory_reset(self):
        """Handle complete memory reset - purge all game memories"""
        try:
            data = self.parse_post_data()
            
            # Require confirmation
            confirm = data.get('confirm', '')
            if confirm != 'RESET':
                raise ValueError("Confirmation required - must provide 'RESET'")
            
            # Create fresh knowledge graph (this will reset everything)
            kg = KnowledgeGraph(self.knowledge_file)
            
            # Clear all data
            kg.locations.clear()
            kg.goals.clear()
            kg.failure_patterns.clear()
            kg.npc_interactions.clear()
            kg.action_history.clear()
            
            # Save the empty knowledge base
            kg.save_knowledge()
            
            # Also clear the notepad file
            notepad_file = "notepad.txt"
            if os.path.exists(notepad_file):
                with open(notepad_file, 'w') as f:
                    f.write(f"Game restarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n\\n")
                    f.write("## Fresh Start\\n")
                    f.write("- All previous memories have been cleared\\n")
                    f.write("- Ready to begin a new Pokemon adventure\\n\\n")
            
            response = {"success": True, "message": "All memory has been reset successfully"}
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            response = {"success": False, "error": str(e)}
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
    
    def log_message(self, format, *args):
        """Suppress HTTP request logging"""
        pass

def start_web_manager(port=8081, knowledge_file="data/knowledge_graph.json"):
    """Start the web management interface"""
    KnowledgeWebManager.knowledge_file = knowledge_file
    
    server = HTTPServer(('localhost', port), KnowledgeWebManager)
    print(f"🛠️ Knowledge Manager starting at http://localhost:{port}")
    print("📝 Create, edit, and manage AI goals and knowledge")
    print("🎯 Full CRUD operations available!")
    print("\nPress Ctrl+C to stop the server\n")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Knowledge Manager stopped")
        server.shutdown()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Start knowledge web manager")
    parser.add_argument("--port", "-p", type=int, default=8081, help="Port to run on")
    parser.add_argument("--file", "-f", default="data/knowledge_graph.json", help="Knowledge file to manage")
    
    args = parser.parse_args()
    start_web_manager(args.port, args.file)
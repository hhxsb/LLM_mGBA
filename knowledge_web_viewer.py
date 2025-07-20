#!/usr/bin/env python3
"""
Web-based Knowledge Viewer - Real-time monitoring of AI's knowledge
"""
import json
import os
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading

class KnowledgeWebViewer(BaseHTTPRequestHandler):
    knowledge_file = "data/knowledge_graph.json"
    
    def do_GET(self):
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/':
            self.serve_dashboard()
        elif parsed_path.path == '/api/knowledge':
            self.serve_knowledge_api()
        elif parsed_path.path == '/api/refresh':
            self.serve_refresh_api()
        else:
            self.send_error(404)
    
    def serve_dashboard(self):
        """Serve the main dashboard HTML"""
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>Pokemon AI Knowledge Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .stat-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }
        .stat-number { font-size: 2em; font-weight: bold; color: #3498db; }
        .stat-label { color: #7f8c8d; margin-top: 5px; }
        .section { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .section h2 { margin-top: 0; color: #2c3e50; border-bottom: 2px solid #ecf0f1; padding-bottom: 10px; }
        .location-item, .goal-item, .action-item { margin: 10px 0; padding: 10px; background: #f8f9fa; border-left: 4px solid #3498db; }
        .goal-active { border-left-color: #27ae60; }
        .goal-completed { border-left-color: #95a5a6; opacity: 0.7; }
        .goal-failed { border-left-color: #e74c3c; }
        .action-success { border-left-color: #27ae60; }
        .action-failure { border-left-color: #e74c3c; }
        .refresh-btn { background: #3498db; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; }
        .refresh-btn:hover { background: #2980b9; }
        .timestamp { color: #7f8c8d; font-size: 0.9em; }
        .priority { background: #e74c3c; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.8em; }
        .no-data { text-align: center; color: #7f8c8d; padding: 40px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🧠 Pokemon AI Knowledge Dashboard</h1>
        <p>Real-time monitoring of what the AI is learning while playing Pokemon</p>
        <button class="refresh-btn" onclick="refreshData()">🔄 Refresh Data</button>
        <span class="timestamp" id="lastUpdate"></span>
    </div>
    
    <div class="stats" id="stats">
        <div class="stat-card">
            <div class="stat-number" id="locationCount">-</div>
            <div class="stat-label">Locations Discovered</div>
        </div>
        <div class="stat-card">
            <div class="stat-number" id="goalCount">-</div>
            <div class="stat-label">Active Goals</div>
        </div>
        <div class="stat-card">
            <div class="stat-number" id="failureCount">-</div>
            <div class="stat-label">Patterns Learned</div>
        </div>
        <div class="stat-card">
            <div class="stat-number" id="actionCount">-</div>
            <div class="stat-label">Actions Recorded</div>
        </div>
    </div>
    
    <div class="section">
        <h2>🎯 Current Goals</h2>
        <div id="goals">
            <div class="no-data">Loading goals...</div>
        </div>
    </div>
    
    <div class="section">
        <h2>📍 Recent Locations</h2>
        <div id="locations">
            <div class="no-data">Loading locations...</div>
        </div>
    </div>
    
    <div class="section">
        <h2>📝 Recent Actions</h2>
        <div id="actions">
            <div class="no-data">Loading actions...</div>
        </div>
    </div>
    
    <div class="section">
        <h2>❌ Learned Patterns</h2>
        <div id="patterns">
            <div class="no-data">Loading patterns...</div>
        </div>
    </div>

    <script>
        function formatTime(timestamp) {
            return new Date(timestamp * 1000).toLocaleTimeString();
        }
        
        function formatDate(timestamp) {
            return new Date(timestamp * 1000).toLocaleString();
        }
        
        function refreshData() {
            fetch('/api/knowledge')
                .then(response => response.json())
                .then(data => {
                    updateStats(data);
                    updateGoals(data.goals || {});
                    updateLocations(data.locations || {});
                    updateActions(data.action_history || []);
                    updatePatterns(data.failure_patterns || {});
                    document.getElementById('lastUpdate').textContent = 'Last updated: ' + new Date().toLocaleTimeString();
                })
                .catch(error => {
                    console.error('Error fetching data:', error);
                    document.getElementById('lastUpdate').textContent = 'Error loading data';
                });
        }
        
        function updateStats(data) {
            document.getElementById('locationCount').textContent = Object.keys(data.locations || {}).length;
            document.getElementById('goalCount').textContent = Object.values(data.goals || {}).filter(g => g.status === 'active').length;
            document.getElementById('failureCount').textContent = Object.keys(data.failure_patterns || {}).length;
            document.getElementById('actionCount').textContent = (data.action_history || []).length;
        }
        
        function updateGoals(goals) {
            const container = document.getElementById('goals');
            if (Object.keys(goals).length === 0) {
                container.innerHTML = '<div class="no-data">No goals detected yet</div>';
                return;
            }
            
            const goalsList = Object.values(goals)
                .sort((a, b) => b.priority - a.priority)
                .slice(0, 10);
            
            container.innerHTML = goalsList.map(goal => `
                <div class="goal-item goal-${goal.status}">
                    <strong>${goal.description}</strong>
                    <span class="priority">Priority: ${goal.priority}</span>
                    <div class="timestamp">Status: ${goal.status} | Created: ${formatDate(goal.created_time)}</div>
                </div>
            `).join('');
        }
        
        function updateLocations(locations) {
            const container = document.getElementById('locations');
            if (Object.keys(locations).length === 0) {
                container.innerHTML = '<div class="no-data">No locations discovered yet</div>';
                return;
            }
            
            const locationsList = Object.values(locations)
                .sort((a, b) => b.last_visited - a.last_visited)
                .slice(0, 10);
            
            container.innerHTML = locationsList.map(loc => `
                <div class="location-item">
                    <strong>${loc.name}</strong> (${loc.coordinates[0]}, ${loc.coordinates[1]})
                    <div class="timestamp">Visited ${loc.visited_count} times | Last: ${formatTime(loc.last_visited)}</div>
                </div>
            `).join('');
        }
        
        function updateActions(actions) {
            const container = document.getElementById('actions');
            if (actions.length === 0) {
                container.innerHTML = '<div class="no-data">No actions recorded yet</div>';
                return;
            }
            
            const recentActions = actions.slice(-10).reverse();
            
            container.innerHTML = recentActions.map(action => `
                <div class="action-item action-${action.success ? 'success' : 'failure'}">
                    <strong>${action.action}</strong>
                    <div class="timestamp">${formatTime(action.timestamp)} | ${action.success ? '✅' : '❌'} | ${action.result.substring(0, 100)}...</div>
                </div>
            `).join('');
        }
        
        function updatePatterns(patterns) {
            const container = document.getElementById('patterns');
            if (Object.keys(patterns).length === 0) {
                container.innerHTML = '<div class="no-data">No patterns learned yet</div>';
                return;
            }
            
            const patternsList = Object.values(patterns)
                .sort((a, b) => b.occurrence_count - a.occurrence_count)
                .slice(0, 5);
            
            container.innerHTML = patternsList.map(pattern => `
                <div class="action-item">
                    <strong>Situation:</strong> ${pattern.situation}<br>
                    <strong>Failed actions:</strong> ${pattern.failed_actions.join(', ')}<br>
                    ${pattern.successful_alternative ? `<strong>Alternative:</strong> ${pattern.successful_alternative}<br>` : ''}
                    <div class="timestamp">Occurred ${pattern.occurrence_count} times | Last: ${formatTime(pattern.last_seen)}</div>
                </div>
            `).join('');
        }
        
        // Auto-refresh every 5 seconds
        setInterval(refreshData, 5000);
        
        // Initial load
        refreshData();
    </script>
</body>
</html>
        """
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())
    
    def serve_knowledge_api(self):
        """Serve knowledge data as JSON API"""
        try:
            if os.path.exists(self.knowledge_file):
                with open(self.knowledge_file, 'r') as f:
                    data = json.load(f)
            else:
                data = {}
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
            
        except Exception as e:
            self.send_error(500, str(e))
    
    def serve_refresh_api(self):
        """Force refresh endpoint"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "refreshed"}).encode())
    
    def log_message(self, format, *args):
        """Suppress HTTP request logging"""
        pass

def start_web_viewer(port=8080, knowledge_file="data/knowledge_graph.json"):
    """Start the web viewer server"""
    KnowledgeWebViewer.knowledge_file = knowledge_file
    
    server = HTTPServer(('localhost', port), KnowledgeWebViewer)
    print(f"🌐 Knowledge Dashboard starting at http://localhost:{port}")
    print("🔄 Auto-refreshes every 5 seconds")
    print("📊 Monitor AI's learning in real-time!")
    print("\nPress Ctrl+C to stop the server\n")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Knowledge Dashboard stopped")
        server.shutdown()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Start knowledge web viewer")
    parser.add_argument("--port", "-p", type=int, default=8080, help="Port to run on")
    parser.add_argument("--file", "-f", default="data/knowledge_graph.json", help="Knowledge file to monitor")
    
    args = parser.parse_args()
    start_web_viewer(args.port, args.file)
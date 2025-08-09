/**
 * Dashboard main JavaScript file
 * Handles dashboard-specific functionality and WebSocket integration
 */

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('🎮 Pokemon AI Dashboard loaded');
    
    // Initialize any dashboard-specific features
    initializeDashboard();
});

function initializeDashboard() {
    // Add any dashboard initialization logic here
    console.log('📊 Dashboard initialized');
    
    // Set up periodic status updates if on dashboard page
    if (window.location.pathname === '/' || window.location.pathname === '/dashboard/') {
        startStatusUpdates();
    }
}

function startStatusUpdates() {
    // Periodically refresh system status on the main dashboard
    setInterval(() => {
        if (window.dashboardWS && window.dashboardWS.isConnected) {
            window.dashboardWS.send({
                type: 'get_status',
                timestamp: Date.now()
            });
        }
    }, 30000); // Every 30 seconds
}

// Global functions for dashboard interactions
window.clearChat = function() {
    if (window.dashboardWS) {
        window.dashboardWS.clearChat();
    }
};

window.exportMessages = function() {
    if (window.dashboardWS) {
        window.dashboardWS.exportMessages();
    }
};
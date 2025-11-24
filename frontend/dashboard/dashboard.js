// Rate Limiter Dashboard JavaScript

class RateLimiterDashboard {
    constructor() {
        this.baseURL = 'http://localhost:8000';
        this.refreshInterval = null;
        this.clients = new Map();
        this.bannedIPs = new Set();
        this.requestHistory = [];
        
        this.init();
    }
    
    async init() {
        await this.checkSystemHealth();
        await this.refreshData();
        this.startAutoRefresh();
    }
    
    async checkSystemHealth() {
        try {
            const response = await fetch(`${this.baseURL}/health`);
            const data = await response.json();
            
            const statusElement = document.getElementById('system-status');
            if (data.status === 'healthy') {
                statusElement.innerHTML = '<span class="badge bg-success status-badge">Healthy</span>';
            } else {
                statusElement.innerHTML = '<span class="badge bg-danger status-badge">Unhealthy</span>';
            }
            
            return data.status === 'healthy';
        } catch (error) {
            document.getElementById('system-status').innerHTML = 
                '<span class="badge bg-danger status-badge">Offline</span>';
            console.error('Health check failed:', error);
            return false;
        }
    }
    
    async refreshData() {
        await Promise.all([
            this.updateMetrics(),
            this.updateTrafficTable(),
            this.updateAlgorithmStats()
        ]);
    }
    
    async updateMetrics() {
        // Update basic metrics
        document.getElementById('active-clients').textContent = this.clients.size;
        
        const blockedCount = Array.from(this.clients.values())
            .filter(client => client.is_blocked).length;
        document.getElementById('blocked-count').textContent = blockedCount;
        
        // Calculate requests per minute
        const now = Date.now();
        const oneMinuteAgo = now - 60000;
        const recentRequests = this.requestHistory.filter(req => req.timestamp > oneMinuteAgo);
        document.getElementById('requests-per-min').textContent = recentRequests.length;
    }
    
    async updateTrafficTable() {
        const tbody = document.getElementById('traffic-table');
        
        if (this.clients.size === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center text-muted">
                        No active clients. Make some requests to see traffic data.
                    </td>
                </tr>
            `;
            return;
        }
        
        let html = '';
        for (const [clientIP, clientData] of this.clients) {
            const statusBadge = clientData.is_blocked 
                ? '<span class="badge bg-danger">Blocked</span>'
                : '<span class="badge bg-success">Active</span>';
                
            const algorithmBadge = this.getAlgorithmBadge(clientData.algorithm || 'unknown');
            
            html += `
                <tr class="client-row" onclick="showClientDetails('${clientIP}')">
                    <td><code>${clientIP}</code></td>
                    <td>${algorithmBadge}</td>
                    <td>${clientData.current_count || 0}/${clientData.limit || 5}</td>
                    <td>${clientData.remaining || 0}</td>
                    <td>${statusBadge}</td>
                    <td>${this.formatTime(clientData.last_request || Date.now())}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-warning me-1" 
                                onclick="event.stopPropagation(); resetClient('${clientIP}')">
                            <i class="fas fa-undo"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger" 
                                onclick="event.stopPropagation(); banClient('${clientIP}')">
                            <i class="fas fa-ban"></i>
                        </button>
                    </td>
                </tr>
            `;
        }
        
        tbody.innerHTML = html;
    }
    
    getAlgorithmBadge(algorithm) {
        const badges = {
            'fixed_window': '<span class="badge bg-warning">Fixed</span>',
            'atomic_fixed_window': '<span class="badge bg-info">Atomic</span>',
            'sliding_window': '<span class="badge bg-success">Sliding</span>',
            'unknown': '<span class="badge bg-secondary">Unknown</span>'
        };
        return badges[algorithm] || badges.unknown;
    }
    
    async updateAlgorithmStats() {
        const algorithms = ['fixed', 'atomic', 'sliding'];
        
        for (const algorithm of algorithms) {
            try {
                const response = await fetch(`${this.baseURL}/status/${algorithm}/dashboard_test`);
                const data = await response.json();
                
                document.getElementById(`${algorithm}-count`).textContent = 
                    `${data.current_count || 0}/${data.limit || 5}`;
                    
                const statusElement = document.getElementById(`${algorithm}-status`);
                if (data.is_blocked) {
                    statusElement.className = 'badge bg-danger';
                    statusElement.textContent = 'Blocked';
                } else {
                    statusElement.className = 'badge bg-success';
                    statusElement.textContent = 'Active';
                }
            } catch (error) {
                document.getElementById(`${algorithm}-status`).innerHTML = 
                    '<span class="badge bg-secondary">Error</span>';
            }
        }
    }
    
    async testAlgorithm(algorithm) {
        const button = event.target.closest('button');
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Testing...';
        
        try {
            const response = await fetch(`${this.baseURL}/test/${algorithm}`);
            const data = await response.json();
            
            // Add to request history
            this.requestHistory.push({
                timestamp: Date.now(),
                algorithm: algorithm,
                allowed: response.status === 200,
                clientIP: 'dashboard_test'
            });
            
            // Update client data
            if (data.rate_limit_info) {
                this.clients.set('dashboard_test', {
                    ...data.rate_limit_info,
                    algorithm: algorithm,
                    last_request: Date.now(),
                    is_blocked: response.status === 429
                });
            }
            
            // Show result
            if (response.status === 200) {
                this.showNotification('success', `${algorithm} test passed!`);
            } else {
                this.showNotification('warning', `${algorithm} test rate limited`);
            }
            
        } catch (error) {
            this.showNotification('error', `${algorithm} test failed: ${error.message}`);
        } finally {
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-play"></i> Test';
            await this.refreshData();
        }
    }
    
    async resetClient(clientIP) {
        try {
            const response = await fetch(`${this.baseURL}/admin/reset/sliding/${clientIP}`, {
                method: 'POST'
            });
            const data = await response.json();
            
            if (data.reset_successful) {
                this.clients.delete(clientIP);
                this.showNotification('success', `Reset successful for ${clientIP}`);
                await this.refreshData();
            } else {
                this.showNotification('error', 'Reset failed');
            }
        } catch (error) {
            this.showNotification('error', `Reset failed: ${error.message}`);
        }
    }
    
    async banClient(clientIP) {
        this.bannedIPs.add(clientIP);
        this.clients.delete(clientIP);
        this.updateBannedList();
        this.showNotification('warning', `Banned ${clientIP}`);
        await this.refreshData();
    }
    
    async resetAllClients() {
        if (!confirm('Are you sure you want to reset all rate limits?')) return;
        
        const algorithms = ['fixed', 'atomic', 'sliding'];
        let resetCount = 0;
        
        for (const [clientIP] of this.clients) {
            for (const algorithm of algorithms) {
                try {
                    await fetch(`${this.baseURL}/admin/reset/${algorithm}/${clientIP}`, {
                        method: 'POST'
                    });
                    resetCount++;
                } catch (error) {
                    console.error(`Failed to reset ${algorithm} for ${clientIP}:`, error);
                }
            }
        }
        
        this.clients.clear();
        this.showNotification('success', `Reset ${resetCount} rate limits`);
        await this.refreshData();
    }
    
    async simulateLoad() {
        const button = event.target;
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Simulating...';
        
        try {
            // Simulate multiple requests
            const promises = [];
            for (let i = 0; i < 10; i++) {
                promises.push(
                    fetch(`${this.baseURL}/test/sliding`).then(response => {
                        this.requestHistory.push({
                            timestamp: Date.now(),
                            algorithm: 'sliding',
                            allowed: response.status === 200,
                            clientIP: 'load_test'
                        });
                        return response;
                    })
                );
            }
            
            await Promise.all(promises);
            this.showNotification('info', 'Load test completed - 10 requests sent');
            
        } catch (error) {
            this.showNotification('error', `Load test failed: ${error.message}`);
        } finally {
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-bolt"></i> Simulate Load Test';
            await this.refreshData();
        }
    }
    
    exportLogs() {
        const logs = {
            timestamp: new Date().toISOString(),
            clients: Array.from(this.clients.entries()),
            requestHistory: this.requestHistory,
            bannedIPs: Array.from(this.bannedIPs)
        };
        
        const blob = new Blob([JSON.stringify(logs, null, 2)], {
            type: 'application/json'
        });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `rate-limiter-logs-${Date.now()}.json`;
        a.click();
        
        URL.revokeObjectURL(url);
        this.showNotification('success', 'Logs exported successfully');
    }
    
    updateBannedList() {
        const container = document.getElementById('banned-list');
        if (this.bannedIPs.size === 0) {
            container.innerHTML = '<span class="badge bg-secondary">No banned IPs</span>';
        } else {
            let html = '';
            for (const ip of this.bannedIPs) {
                html += `
                    <span class="badge bg-danger me-1 mb-1">
                        ${ip}
                        <button type="button" class="btn-close btn-close-white ms-1" 
                                onclick="dashboard.unbanIP('${ip}')" style="font-size: 0.6rem;"></button>
                    </span>
                `;
            }
            container.innerHTML = html;
        }
    }
    
    unbanIP(ip) {
        this.bannedIPs.delete(ip);
        this.updateBannedList();
        this.showNotification('info', `Unbanned ${ip}`);
    }
    
    formatTime(timestamp) {
        return new Date(timestamp).toLocaleTimeString();
    }
    
    showNotification(type, message) {
        // Create a simple notification
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 300px;';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 3 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 3000);
    }
    
    startAutoRefresh() {
        // Refresh every 5 seconds
        this.refreshInterval = setInterval(() => {
            this.refreshData();
        }, 5000);
    }
    
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }
}

// Global dashboard instance
let dashboard;

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', () => {
    dashboard = new RateLimiterDashboard();
});

// Global functions for HTML onclick handlers
function refreshData() {
    dashboard.refreshData();
}

function testAlgorithm(algorithm) {
    dashboard.testAlgorithm(algorithm);
}

function resetClient(clientIP) {
    dashboard.resetClient(clientIP);
}

function banClient(clientIP) {
    dashboard.banClient(clientIP);
}

function resetAllClients() {
    dashboard.resetAllClients();
}

function simulateLoad() {
    dashboard.simulateLoad();
}

function exportLogs() {
    dashboard.exportLogs();
}

function clearAllLimits() {
    dashboard.resetAllClients();
}

function banIP(event) {
    event.preventDefault();
    const input = document.getElementById('ban-ip-input');
    const ip = input.value.trim();
    
    if (ip) {
        dashboard.banClient(ip);
        input.value = '';
    }
}

function showClientDetails(clientIP) {
    const client = dashboard.clients.get(clientIP);
    if (!client) return;
    
    const details = `
        Client: ${clientIP}
        Algorithm: ${client.algorithm || 'Unknown'}
        Current Count: ${client.current_count || 0}
        Limit: ${client.limit || 5}
        Remaining: ${client.remaining || 0}
        Status: ${client.is_blocked ? 'Blocked' : 'Active'}
        Last Request: ${dashboard.formatTime(client.last_request || Date.now())}
    `;
    
    alert(details);
}
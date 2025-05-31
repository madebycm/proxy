// WebSocket connection
const socket = io();

// State
let proxyState = {
    running: false,
    port: 4545,
    mode: 'minimal',
    requests_count: 0,
    start_time: null
};

let requests = [];
let interceptorRules = {};
let uptimeInterval = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    setupWebSocket();
    loadConfigurations();
    updateUI();
});

// Event Listeners
function setupEventListeners() {
    document.getElementById('start-btn').addEventListener('click', startProxy);
    document.getElementById('stop-btn').addEventListener('click', stopProxy);
    document.getElementById('clear-btn').addEventListener('click', clearLogs);
    document.getElementById('search-input').addEventListener('input', filterRequests);
    document.getElementById('method-filter').addEventListener('change', filterRequests);
}

// WebSocket Setup
function setupWebSocket() {
    socket.on('connect', () => {
        console.log('Connected to WebSocket');
    });

    socket.on('proxy_state', (state) => {
        proxyState = state;
        updateUI();
    });

    socket.on('new_request', (request) => {
        addRequest(request);
    });

    socket.on('disconnect', () => {
        console.log('Disconnected from WebSocket');
    });
}

// Proxy Control
async function startProxy() {
    const port = document.getElementById('proxy-port').value;
    const mode = document.getElementById('proxy-mode').value;

    try {
        const response = await fetch('/api/proxy/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ port: parseInt(port), mode })
        });

        const data = await response.json();
        if (!response.ok) {
            alert(`Error: ${data.error}`);
        }
    } catch (error) {
        alert(`Failed to start proxy: ${error.message}`);
    }
}

async function stopProxy() {
    try {
        const response = await fetch('/api/proxy/stop', {
            method: 'POST'
        });

        const data = await response.json();
        if (!response.ok) {
            alert(`Error: ${data.error}`);
        }
    } catch (error) {
        alert(`Failed to stop proxy: ${error.message}`);
    }
}

// UI Updates
function updateUI() {
    // Update status
    const statusEl = document.getElementById('status');
    statusEl.textContent = proxyState.running ? 'Online' : 'Offline';
    statusEl.className = proxyState.running ? 'status-value online' : 'status-value offline';

    // Update port
    document.getElementById('port').textContent = proxyState.running ? proxyState.port : '-';

    // Update request count
    document.getElementById('request-count').textContent = proxyState.requests_count;

    // Update buttons
    document.getElementById('start-btn').disabled = proxyState.running;
    document.getElementById('stop-btn').disabled = !proxyState.running;
    document.getElementById('proxy-port').disabled = proxyState.running;
    document.getElementById('proxy-mode').disabled = proxyState.running;

    // Update uptime
    if (proxyState.running && proxyState.start_time) {
        if (!uptimeInterval) {
            uptimeInterval = setInterval(updateUptime, 1000);
        }
        updateUptime();
    } else {
        if (uptimeInterval) {
            clearInterval(uptimeInterval);
            uptimeInterval = null;
        }
        document.getElementById('uptime').textContent = '-';
    }
}

function updateUptime() {
    if (!proxyState.start_time) return;

    const start = new Date(proxyState.start_time);
    const now = new Date();
    const diff = Math.floor((now - start) / 1000);

    const hours = Math.floor(diff / 3600);
    const minutes = Math.floor((diff % 3600) / 60);
    const seconds = diff % 60;

    const parts = [];
    if (hours > 0) parts.push(`${hours}h`);
    if (minutes > 0) parts.push(`${minutes}m`);
    parts.push(`${seconds}s`);

    document.getElementById('uptime').textContent = parts.join(' ');
}

// Request Management
function addRequest(request) {
    // Handle response data
    if (request.type === 'response') {
        // Find the last request and add response data
        const lastRequest = requests[requests.length - 1];
        if (lastRequest) {
            lastRequest.response = request;
        }
        // Add response item to the list
        addResponseItem(request);
        return;
    }

    requests.push(request);
    
    const listEl = document.getElementById('request-list');
    
    // Remove empty state
    const emptyState = listEl.querySelector('.empty-state');
    if (emptyState) {
        emptyState.remove();
    }

    // Create request element
    const requestEl = document.createElement('div');
    requestEl.className = 'request-item';
    requestEl.dataset.requestId = request.id;
    requestEl.innerHTML = `
        <div class="request-header">
            <span class="request-method method-${request.method}">${request.method}</span>
            <span class="request-time">${request.timestamp}</span>
        </div>
        <div class="request-url">${request.url}</div>
        <div class="request-meta">
            <span>Host: ${request.host}</span>
            <span>App: ${request.app}</span>
        </div>
    `;

    requestEl.addEventListener('click', () => showRequestDetails(request));

    // Prepend to list (newest first)
    listEl.insertBefore(requestEl, listEl.firstChild);

    // Limit displayed requests
    if (listEl.children.length > 500) {
        listEl.removeChild(listEl.lastChild);
    }
}

function addResponseItem(response) {
    const listEl = document.getElementById('request-list');
    
    // Create response element
    const responseEl = document.createElement('div');
    responseEl.className = 'request-item response';
    responseEl.innerHTML = `
        <div class="request-header">
            <span class="request-method">Response ${response.status}</span>
            <span class="request-time">${response.timestamp}</span>
        </div>
        <div class="request-meta">
            <span>${response.content_type || 'No content type'}</span>
        </div>
    `;

    // Insert after the first request item
    if (listEl.firstChild && !listEl.firstChild.classList.contains('response')) {
        listEl.insertBefore(responseEl, listEl.firstChild.nextSibling);
    }
}

function clearRequests() {
    requests = [];
    const listEl = document.getElementById('request-list');
    listEl.innerHTML = '<div class="empty-state">No requests yet. Start the proxy to begin monitoring.</div>';
}

function filterRequests() {
    const searchTerm = document.getElementById('search-input').value.toLowerCase();
    const methodFilter = document.getElementById('method-filter').value;

    const items = document.querySelectorAll('.request-item');
    items.forEach(item => {
        const url = item.querySelector('.request-url')?.textContent.toLowerCase() || '';
        const method = item.querySelector('.request-method')?.textContent || '';

        const matchesSearch = !searchTerm || url.includes(searchTerm);
        const matchesMethod = !methodFilter || method === methodFilter;

        item.style.display = matchesSearch && matchesMethod ? 'block' : 'none';
    });
}

// Request Details Modal
function showRequestDetails(request) {
    const modal = document.getElementById('request-modal');
    const details = document.getElementById('request-details');

    let detailsHtml = `
        <h3>Request</h3>
        <pre>
${request.method} ${request.url}
Host: ${request.host}
Path: ${request.path}
Application: ${request.app}
Time: ${request.timestamp}
        </pre>
    `;

    if (request.response) {
        detailsHtml += `
        <h3>Response</h3>
        <pre>
Status: ${request.response.status}
Content-Type: ${request.response.content_type || 'N/A'}
        </pre>
        `;
    }

    details.innerHTML = detailsHtml;
    modal.style.display = 'block';
}

function closeModal() {
    document.getElementById('request-modal').style.display = 'none';
}

function showCertificateInstructions() {
    document.getElementById('cert-modal').style.display = 'block';
}

function closeCertModal() {
    document.getElementById('cert-modal').style.display = 'none';
}

// Tab Management
function showTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.toggle('active', tab.textContent.toLowerCase().includes(tabName.toLowerCase()));
    });

    // Update tab panes
    document.querySelectorAll('.tab-pane').forEach(pane => {
        pane.classList.remove('active');
    });
    document.getElementById(`${tabName}-tab`).classList.add('active');
}

// Configuration Management
async function loadConfigurations() {
    // Load blacklist
    try {
        const response = await fetch('/api/config/blacklist');
        const data = await response.json();
        document.getElementById('blacklist-domains').value = data.domains.join('\n');
    } catch (error) {
        console.error('Failed to load blacklist:', error);
    }

    // Load interceptor rules
    try {
        const response = await fetch('/api/config/interceptor');
        const data = await response.json();
        interceptorRules = data.config || {};
        renderInterceptorRules();
    } catch (error) {
        console.error('Failed to load interceptor rules:', error);
    }
}

async function saveBlacklist() {
    const domains = document.getElementById('blacklist-domains').value
        .split('\n')
        .map(d => d.trim())
        .filter(d => d);

    try {
        const response = await fetch('/api/config/blacklist', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ domains })
        });

        if (response.ok) {
            alert('Blacklist saved successfully');
        } else {
            alert('Failed to save blacklist');
        }
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

function renderInterceptorRules() {
    const container = document.getElementById('interceptor-rules');
    container.innerHTML = '';

    Object.entries(interceptorRules).forEach(([pattern, config]) => {
        const ruleEl = createInterceptorRuleElement(pattern, config);
        container.appendChild(ruleEl);
    });
}

function createInterceptorRuleElement(pattern = '', config = {}) {
    const ruleEl = document.createElement('div');
    ruleEl.className = 'interceptor-rule';
    
    const ruleId = Date.now() + Math.random();
    ruleEl.innerHTML = `
        <div class="rule-header">
            <strong>URL Pattern</strong>
            <span class="rule-remove" onclick="removeInterceptorRule('${ruleId}')">&times;</span>
        </div>
        <input type="text" placeholder="example.com/api" value="${pattern}" data-field="pattern">
        <input type="number" placeholder="Status Code (e.g., 200)" value="${config.status || 200}" data-field="status">
        <textarea placeholder="Response Content (text or JSON)" data-field="content">${
            typeof config.content === 'object' ? JSON.stringify(config.content, null, 2) : (config.content || '')
        }</textarea>
        <input type="text" placeholder="Content-Type (e.g., application/json)" value="${
            config.headers?.['Content-Type'] || 'text/plain'
        }" data-field="content-type">
    `;

    ruleEl.dataset.ruleId = ruleId;
    return ruleEl;
}

function addInterceptorRule() {
    const container = document.getElementById('interceptor-rules');
    const ruleEl = createInterceptorRuleElement();
    container.appendChild(ruleEl);
}

function removeInterceptorRule(ruleId) {
    const rule = document.querySelector(`[data-rule-id="${ruleId}"]`);
    if (rule) {
        rule.remove();
    }
}

async function saveInterceptorRules() {
    const rules = {};
    
    document.querySelectorAll('.interceptor-rule').forEach(ruleEl => {
        const pattern = ruleEl.querySelector('[data-field="pattern"]').value.trim();
        if (!pattern) return;

        const status = parseInt(ruleEl.querySelector('[data-field="status"]').value) || 200;
        const contentText = ruleEl.querySelector('[data-field="content"]').value.trim();
        const contentType = ruleEl.querySelector('[data-field="content-type"]').value.trim() || 'text/plain';

        let content = contentText;
        // Try to parse as JSON if content type is JSON
        if (contentType.includes('json') && contentText) {
            try {
                content = JSON.parse(contentText);
            } catch (e) {
                // Keep as string if JSON parsing fails
            }
        }

        rules[pattern] = {
            status,
            content,
            headers: {
                'Content-Type': contentType,
                'X-Intercepted': 'true'
            }
        };
    });

    try {
        const response = await fetch('/api/config/interceptor', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ config: rules })
        });

        if (response.ok) {
            interceptorRules = rules;
            alert('Interceptor rules saved successfully');
        } else {
            alert('Failed to save interceptor rules');
        }
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

async function clearLogs() {
    if (!confirm('Are you sure you want to clear all log files?')) {
        return;
    }

    try {
        const response = await fetch('/api/logs/clear', {
            method: 'POST'
        });

        if (response.ok) {
            alert('Logs cleared successfully');
        } else {
            alert('Failed to clear logs');
        }
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

// Close modals when clicking outside
window.onclick = function(event) {
    if (event.target.className === 'modal') {
        event.target.style.display = 'none';
    }
}
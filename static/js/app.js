// PyWemo API Client
class PyWemoClient {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl;
    }

    async request(url, options = {}) {
        try {
            const response = await fetch(this.baseUrl + url, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API Request Error:', error);
            throw error;
        }
    }

    async getDevices() {
        return this.request('/devices');
    }

    async refreshDevices(options = {}) {
        const { networkScan = false, timeout = 10, customNetwork = null } = options;
        return this.request('/devices/refresh', { 
            method: 'POST',
            body: JSON.stringify({ 
                network_scan: networkScan, 
                timeout,
                custom_network: customNetwork
            })
        });
    }

    async getDiscoveryStatus() {
        return this.request('/devices/discovery/status');
    }

    async triggerNetworkScan(timeout = 15, customNetwork = null) {
        return this.request('/devices/discovery/network-scan', {
            method: 'POST',
            body: JSON.stringify({ 
                timeout,
                custom_network: customNetwork
            })
        });
    }

    async toggleAutoDiscovery(enable) {
        return this.request('/devices/discovery/toggle', {
            method: 'POST',
            body: JSON.stringify({ enable })
        });
    }

    async discoverDeviceByIP(ip) {
        return this.request('/device/discover_by_ip', {
            method: 'POST',
            body: JSON.stringify({ ip })
        });
    }

    async getDeviceMethods(udn) {
        return this.request(`/device/${encodeURIComponent(udn)}/methods`);
    }

    async callDeviceMethod(udn, method, args = [], kwargs = {}) {
        return this.request(`/device/${encodeURIComponent(udn)}/${encodeURIComponent(method)}`, {
            method: 'POST',
            body: JSON.stringify({ args, kwargs })
        });
    }

    async forgetDevice(udn) {
        return this.request(`/device/${encodeURIComponent(udn)}/forget`, {
            method: 'POST'
        });
    }

    async forgetAllDevices() {
        return this.request('/devices/forget_all', {
            method: 'POST'
        });
    }

    async validateNetwork(network) {
        return this.request('/devices/network/validate', {
            method: 'POST',
            body: JSON.stringify({ network })
        });
    }

    async getScanProgress() {
        return this.request('/devices/scan/progress');
    }

    async cancelScan() {
        return this.request('/devices/scan/cancel', {
            method: 'POST'
        });
    }

    async turnAllDevicesOn() {
        return this.request('/devices/bulk/turn_on', {
            method: 'POST'
        });
    }

    async turnAllDevicesOff() {
        return this.request('/devices/bulk/turn_off', {
            method: 'POST'
        });
    }

    async getDevicesStatus() {
        return this.request('/devices/status');
    }

    async getDeviceFriendlyName(udn) {
        return this.request(`/device/${encodeURIComponent(udn)}/friendly-name`);
    }

    async setDeviceFriendlyName(udn, friendlyName) {
        return this.request(`/device/${encodeURIComponent(udn)}/friendly-name`, {
            method: 'POST',
            body: JSON.stringify({ friendly_name: friendlyName })
        });
    }

    async deleteDeviceFriendlyName(udn) {
        return this.request(`/device/${encodeURIComponent(udn)}/friendly-name`, {
            method: 'DELETE'
        });
    }
}

// Global variables
const client = new PyWemoClient();
let devices = [];
let deviceStates = new Map(); // Track device states
let currentDevice = null;
let currentMethod = null;
let lastValidatedNetwork = null;

// Theme management
let currentTheme = localStorage.getItem('theme') || 'auto';
let systemThemeQuery = null;
let isSystemDark = false;

// Scan progress tracking
let scanProgressInterval = null;
let isScanning = false;

// Device status polling
let statusPollingInterval = null;
let isStatusPollingEnabled = localStorage.getItem('statusPollingEnabled') === 'true';
let statusPollingFrequency = parseInt(localStorage.getItem('statusPollingFrequency')) || 30; // seconds
let lastStatusUpdate = null;

// DOM elements
const refreshBtn = document.getElementById('refreshBtn');
const addDeviceBtn = document.getElementById('addDeviceBtn');
const customNetworkScanBtn = document.getElementById('customNetworkScanBtn');
const statusEl = document.getElementById('status');
const devicesContainer = document.getElementById('devicesContainer');
const addDeviceModal = document.getElementById('addDeviceModal');
const customNetworkModal = document.getElementById('customNetworkModal');
const methodModal = document.getElementById('methodModal');
const argsModal = document.getElementById('argsModal');

// Utility functions
function showStatus(message, type = 'info') {
    statusEl.textContent = message;
    statusEl.className = `status-message status-${type}`;
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        statusEl.textContent = '';
        statusEl.className = 'status-message';
    }, 5000);
}

function showModal(modal) {
    modal.style.display = 'block';
    document.body.style.overflow = 'hidden';
}

function closeModal() {
    addDeviceModal.style.display = 'none';
    document.body.style.overflow = 'auto';
}

function closeMethodModal() {
    methodModal.style.display = 'none';
    document.body.style.overflow = 'auto';
}

function closeArgsModal() {
    argsModal.style.display = 'none';
    document.body.style.overflow = 'auto';
}

function closeCustomNetworkModal() {
    customNetworkModal.style.display = 'none';
    document.body.style.overflow = 'auto';
    // Reset form
    document.getElementById('networkRange').value = '';
    document.getElementById('scanTimeout').value = '15';
    document.getElementById('networkValidationResult').innerHTML = '';
    document.getElementById('startCustomScanBtn').disabled = true;
    lastValidatedNetwork = null;
}

// Device rendering
function renderDevices(devicesData) {
    // Show/hide bulk controls based on device availability
    const bulkControlsSection = document.getElementById('bulkControlsSection');
    
    if (!devicesData || devicesData.length === 0) {
        devicesContainer.innerHTML = `
            <div class="loading">
                <p>No WeMo devices found on your network.</p>
                <p>Try refreshing or adding a device manually by IP address.</p>
            </div>
        `;
        bulkControlsSection.style.display = 'none';
        return;
    }
    
    // Show bulk controls when devices are available
    bulkControlsSection.style.display = 'flex';

    devicesContainer.innerHTML = devicesData.map(device => {
        const deviceState = deviceStates.get(device.udn);
        const stateInfo = getStateDisplay(deviceState);
        
        // Default to online connection status for initial rendering
        // This will be updated by status monitoring if enabled
        const initialConnectionClass = 'card-online';
        
        // Determine display name (friendly name if available, otherwise original name)
        const displayName = device.display_name || device.name;
        const hasCustomName = device.friendly_name && device.friendly_name !== device.name;
        
        return `
        <div class="device-card ${initialConnectionClass}" data-udn="${escapeHtml(device.udn)}">
            <div class="device-header">
                <div>
                    <div class="device-name-container">
                        <div class="device-name" data-device-display-name>${escapeHtml(displayName)}</div>
                        <button class="btn-edit-name" onclick="editDeviceName('${escapeHtml(device.udn)}', '${escapeHtml(displayName)}')" title="Edit device name">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
                            </svg>
                        </button>
                    </div>
                    <div class="device-model">
                        ${escapeHtml(device.model || 'Unknown Model')}
                        ${hasCustomName ? `<span class="original-name-hint" title="Original name: ${escapeHtml(device.name)}">(custom name)</span>` : ''}
                    </div>
                </div>
                <div class="device-state ${stateInfo.className} device-online" data-state-indicator>
                    <div class="state-indicator"></div>
                    ${stateInfo.text}
                </div>
            </div>
            
            <div class="device-info">
                <p><strong>IP Address:</strong> <span class="device-ip">${escapeHtml(device.ip_address || 'Unknown')}</span></p>
                <p><strong>Serial:</strong> ${escapeHtml(device.serial || 'N/A')}</p>
                <p><strong>UDN:</strong> <code>${escapeHtml(device.udn)}</code></p>
            </div>
            
            <div class="device-actions">
                <button class="btn btn-primary" onclick="showDeviceMethods('${escapeHtml(device.udn)}', '${escapeHtml(device.name)}')">
                    🔧 Control Device
                </button>
                <button class="btn btn-success" onclick="quickAction('${escapeHtml(device.udn)}', 'get_state')">
                    📊 Get State
                </button>
                <button class="btn btn-secondary" onclick="quickAction('${escapeHtml(device.udn)}', 'toggle')">
                    🔄 Toggle
                </button>
                <button class="btn btn-danger" onclick="forgetDevice('${escapeHtml(device.udn)}', '${escapeHtml(device.name)}')">
                    🗑️ Forget
                </button>
            </div>
        </div>
        `;
    }).join('');
}

// Helper function to get state display information
function getStateDisplay(state) {
    switch (state) {
        case 1:
            return { className: 'state-on', text: 'ON' };
        case 0:
            return { className: 'state-off', text: 'OFF' };
        default:
            return { className: 'state-unknown', text: 'UNKNOWN' };
    }
}

// Function to update a specific device's state indicator
function updateDeviceStateIndicator(udn, state) {
    deviceStates.set(udn, state);
    const deviceCard = document.querySelector(`[data-udn="${escapeHtml(udn)}"]`);
    if (deviceCard) {
        const stateElement = deviceCard.querySelector('[data-state-indicator]');
        const stateInfo = getStateDisplay(state);
        
        if (stateElement) {
            // Preserve existing connection status classes if they exist
            const existingClasses = stateElement.className.split(' ');
            const connectionClass = existingClasses.find(cls => cls.startsWith('device-'));
            
            // Build the new className, preserving connection class if it exists
            let newClassName = `device-state ${stateInfo.className}`;
            if (connectionClass) {
                newClassName += ` ${connectionClass}`;
            }
            
            stateElement.className = newClassName;
            
            // Update text, preserving offline indicator if connection class indicates offline
            let stateText = stateInfo.text;
            if (connectionClass === 'device-offline') {
                stateText += ' (OFFLINE)';
            }
            
            stateElement.innerHTML = `
                <div class="state-indicator"></div>
                ${stateText}
            `;
        }
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Device name editing functions
async function editDeviceName(udn, currentName) {
    const newName = prompt(`Edit device name:\n\nCurrent: ${currentName}\n\nEnter new friendly name (or leave empty to use original name):`, currentName);
    
    if (newName === null) {
        // User cancelled
        return;
    }
    
    try {
        const trimmedName = newName.trim();
        
        if (trimmedName === '' || trimmedName === currentName) {
            // Remove friendly name or no change
            if (trimmedName === '') {
                showStatus('Removing custom device name...', 'info');
                await client.deleteDeviceFriendlyName(udn);
                showStatus('✅ Device name reset to original', 'success');
            } else {
                showStatus('No changes made to device name', 'info');
                return;
            }
        } else {
            // Set new friendly name
            showStatus(`Setting device name to "${trimmedName}"...`, 'info');
            await client.setDeviceFriendlyName(udn, trimmedName);
            showStatus(`✅ Device name updated to "${trimmedName}"`, 'success');
        }
        
        // Refresh device display to show updated name
        await loadDevices();
        
    } catch (error) {
        showStatus(`Error updating device name: ${error.message}`, 'error');
        console.error('Device name update error:', error);
    }
}

// Update device display name in the UI without full reload
function updateDeviceDisplayName(udn, displayName) {
    const deviceCard = document.querySelector(`[data-udn="${escapeHtml(udn)}"]`);
    if (deviceCard) {
        const nameElement = deviceCard.querySelector('[data-device-display-name]');
        if (nameElement) {
            nameElement.textContent = displayName;
        }
    }
}

// Theme management functions
function initializeTheme() {
    // Set up system theme detection
    if (window.matchMedia) {
        systemThemeQuery = window.matchMedia('(prefers-color-scheme: dark)');
        isSystemDark = systemThemeQuery.matches;
        
        // Listen for system theme changes
        systemThemeQuery.addListener(handleSystemThemeChange);
    }
    
    // Initialize theme selector
    initializeThemeSelector();
    
    // Apply theme
    applyTheme();
    updateThemeSelector();
}

function applyTheme() {
    let effectiveTheme = currentTheme;
    
    // If auto mode, use system preference
    if (currentTheme === 'auto') {
        effectiveTheme = isSystemDark ? 'dark' : 'light';
    }
    
    document.documentElement.setAttribute('data-theme', effectiveTheme);
}

function setTheme(theme) {
    currentTheme = theme;
    
    localStorage.setItem('theme', currentTheme);
    applyTheme();
    updateThemeSelector();
    
    // Show status message
    let message;
    if (currentTheme === 'auto') {
        const systemMode = isSystemDark ? 'dark' : 'light';
        message = `🌑 Auto mode (following system: ${systemMode})`;
    } else {
        message = `🌈 Switched to ${currentTheme} mode`;
    }
    showStatus(message, 'success');
}

function updateThemeSelector() {
    const selector = document.getElementById('themeSelector');
    if (selector) {
        selector.setAttribute('data-theme', currentTheme);
        
        // Remove active class from all options
        const options = selector.querySelectorAll('.theme-option');
        options.forEach(option => option.classList.remove('active'));
        
        // Add active class to current theme option
        const activeOption = selector.querySelector(`.${currentTheme}-option`);
        if (activeOption) {
            activeOption.classList.add('active');
        }
        
        // Update tooltips based on current state
        const lightOption = selector.querySelector('.light-option');
        const darkOption = selector.querySelector('.dark-option');
        const autoOption = selector.querySelector('.auto-option');
        
        if (lightOption) lightOption.title = 'Light theme';
        if (darkOption) darkOption.title = 'Dark theme';
        if (autoOption) {
            const systemMode = isSystemDark ? 'dark' : 'light';
            autoOption.title = `Auto theme (currently: ${systemMode})`;
        }
    }
}

function initializeThemeSelector() {
    const selector = document.getElementById('themeSelector');
    if (selector) {
        // Add click listeners to each theme option
        const options = selector.querySelectorAll('.theme-option');
        options.forEach(option => {
            option.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const theme = option.getAttribute('data-theme');
                if (theme && theme !== currentTheme) {
                    setTheme(theme);
                }
            });
        });
    }
}

function handleSystemThemeChange(e) {
    isSystemDark = e.matches;
    
    // Only apply change if we're in auto mode
    if (currentTheme === 'auto') {
        applyTheme();
        updateThemeSelector();
        
        const systemMode = isSystemDark ? 'dark' : 'light';
        showStatus(`🌑 System theme changed to ${systemMode}`, 'info');
    }
}

// Clock functionality
function updateClock() {
    const now = new Date();
    const clockTime = document.getElementById('clockTime');
    const clockDate = document.getElementById('clockDate');
    
    if (clockTime && clockDate) {
        // Format time as HH:MM:SS
        const timeStr = now.toLocaleTimeString('en-US', {
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
        
        // Format date as Mon, Jan 15
        const dateStr = now.toLocaleDateString('en-US', {
            weekday: 'short',
            month: 'short',
            day: 'numeric'
        });
        
        clockTime.textContent = timeStr;
        clockDate.textContent = dateStr;
    }
}

// Initialize clock and update every second
function initializeClock() {
    updateClock(); // Update immediately
    setInterval(updateClock, 1000); // Update every second
}

// Device methods
async function showDeviceMethods(udn, deviceName) {
    currentDevice = { udn, name: deviceName };
    document.getElementById('methodModalTitle').textContent = `${deviceName} - Available Methods`;
    document.getElementById('methodsContainer').innerHTML = '<div class="loading">Loading methods...</div>';
    
    showModal(methodModal);
    
    try {
        const methods = await client.getDeviceMethods(udn);
        
        if (!methods || methods.length === 0) {
            document.getElementById('methodsContainer').innerHTML = '<p>No public methods available for this device.</p>';
            return;
        }
        
        document.getElementById('methodsContainer').innerHTML = methods.map(method => `
            <div class="method-btn" onclick="prepareMethodCall('${escapeHtml(method)}')">
                ${escapeHtml(method)}
            </div>
        `).join('');
        
    } catch (error) {
        document.getElementById('methodsContainer').innerHTML = `<p class="status-error">Error loading methods: ${error.message}</p>`;
        showStatus(`Error loading methods: ${error.message}`, 'error');
    }
}

function prepareMethodCall(method) {
    currentMethod = method;
    document.getElementById('argsModalTitle').textContent = `${currentDevice.name} - ${method}`;
    document.getElementById('methodArgs').value = '[]';
    document.getElementById('methodKwargs').value = '{}';
    document.getElementById('methodResult').innerHTML = '';
    
    closeMethodModal();
    showModal(argsModal);
}

async function quickAction(udn, method) {
    try {
        showStatus(`Executing ${method}...`, 'info');
        const result = await client.callDeviceMethod(udn, method);
        
        // Handle different method types
        if (method === 'get_state') {
            const state = result.result;
            updateDeviceStateIndicator(udn, state);
            const stateText = state === 1 ? 'ON' : state === 0 ? 'OFF' : 'UNKNOWN';
            const stateEmoji = state === 1 ? '🟢' : state === 0 ? '🔴' : '🟡';
            showStatus(`${stateEmoji} Device state: ${stateText}`, 'success');
        } else if (method === 'toggle' || method === 'on' || method === 'off') {
            // After state-changing operations, automatically get the new state
            setTimeout(async () => {
                try {
                    const stateResult = await client.callDeviceMethod(udn, 'get_state');
                    updateDeviceStateIndicator(udn, stateResult.result);
                } catch (stateError) {
                    console.warn('Failed to refresh state after action:', stateError);
                }
            }, 500); // Small delay to allow device to update
            
            const actionEmoji = method === 'toggle' ? '🔄' : method === 'on' ? '🟢' : '🔴';
            showStatus(`${actionEmoji} ${method.toUpperCase()} command executed successfully!`, 'success');
        } else {
            showStatus(`${method} executed successfully!`, 'success');
        }
        
        console.log('Method result:', result);
    } catch (error) {
        showStatus(`Error executing ${method}: ${error.message}`, 'error');
        console.error('Method error:', error);
    }
}

// Forget a single device
async function forgetDevice(udn, deviceName) {
    if (!confirm(`Are you sure you want to forget "${deviceName}"?\n\nThis will remove the device from the interface, but it can be re-discovered later.`)) {
        return;
    }
    
    try {
        showStatus(`Forgetting device "${deviceName}"...`, 'info');
        const result = await client.forgetDevice(udn);
        
        // Remove device state from local tracking
        deviceStates.delete(udn);
        
        // Refresh the device list
        await loadDevices();
        
        showStatus(`🗑️ Device "${deviceName}" forgotten successfully! (${result.remaining_devices} devices remaining)`, 'success');
        
    } catch (error) {
        showStatus(`Error forgetting device: ${error.message}`, 'error');
        console.error('Forget device error:', error);
    }
}

// Forget all devices
async function forgetAllDevices() {
    const deviceCount = devices.length;
    
    if (deviceCount === 0) {
        showStatus('No devices to forget', 'info');
        return;
    }
    
    if (!confirm(`Are you sure you want to forget ALL ${deviceCount} devices?\n\nThis will remove all devices from the interface, but they can be re-discovered later.`)) {
        return;
    }
    
    try {
        showStatus(`Forgetting all ${deviceCount} devices...`, 'info');
        const result = await client.forgetAllDevices();
        
        // Clear local device states
        deviceStates.clear();
        
        // Refresh the device list
        await loadDevices();
        
        showStatus(`🗑️ All devices forgotten successfully! ${result.forgotten_devices.length} devices removed.`, 'success');
        
    } catch (error) {
        showStatus(`Error forgetting all devices: ${error.message}`, 'error');
        console.error('Forget all devices error:', error);
    }
}

// Load and refresh devices
async function loadDevices() {
    devicesContainer.innerHTML = '<div class="loading">Loading devices...</div>';
    
    try {
        devices = await client.getDevices();
        renderDevices(devices);
        
        // Initialize device states for all discovered devices
        if (devices.length > 0) {
            if (isStatusPollingEnabled) {
                // If status polling is enabled, use batch status update
                await updateDeviceStatuses();
                
                // Ensure status polling is running
                if (!statusPollingInterval) {
                    startStatusPolling();
                }
            } else {
                // Fall back to individual state requests which will also update connection status
                await initializeDeviceStates(devices);
            }
        } else {
            // No devices found, stop status polling
            stopStatusPolling();
        }
        
        showStatus(`Found ${devices.length} device(s)`, 'success');
    } catch (error) {
        devicesContainer.innerHTML = `
            <div class="loading">
                <p>Error loading devices: ${error.message}</p>
                <p>Make sure the PyWemo API is running and accessible.</p>
            </div>
        `;
        showStatus(`Error loading devices: ${error.message}`, 'error');
        stopStatusPolling(); // Stop polling on error
    }
}

// Initialize states for all devices
async function initializeDeviceStates(devicesArray) {
    const statePromises = devicesArray.map(async (device) => {
        const deviceCard = document.querySelector(`[data-udn="${escapeHtml(device.udn)}"]`);
        try {
            const result = await client.callDeviceMethod(device.udn, 'get_state');
            updateDeviceStateIndicator(device.udn, result.result);
            
            // Also update connection status to online since get_state succeeded
            if (deviceCard) {
                deviceCard.classList.remove('card-online', 'card-offline', 'card-unknown');
                deviceCard.classList.add('card-online');
                
                // Update state element to show online connection
                const stateElement = deviceCard.querySelector('[data-state-indicator]');
                if (stateElement) {
                    stateElement.classList.remove('device-offline', 'device-unknown');
                    stateElement.classList.add('device-online');
                }
            }
        } catch (error) {
            console.warn(`Failed to get initial state for device ${device.name}:`, error);
            
            // Mark device as offline since get_state failed
            if (deviceCard) {
                deviceCard.classList.remove('card-online', 'card-offline', 'card-unknown');
                deviceCard.classList.add('card-offline');
                
                // Update state element to show offline connection
                const stateElement = deviceCard.querySelector('[data-state-indicator]');
                if (stateElement) {
                    stateElement.classList.remove('device-online', 'device-unknown');
                    stateElement.classList.add('device-offline');
                    
                    // Update text to show offline status
                    const currentText = stateElement.textContent.replace(' (OFFLINE)', '');
                    stateElement.innerHTML = `
                        <div class="state-indicator"></div>
                        ${currentText} (OFFLINE)
                    `;
                }
            }
        }
    });
    
    // Wait for all state requests to complete (or fail)
    await Promise.allSettled(statePromises);
}

async function refreshDevices(networkScan = false) {
    // Check if already scanning for network scans
    if (networkScan && isScanning) {
        showStatus('Scan already in progress', 'info');
        return;
    }
    
    refreshBtn.disabled = true;
    const originalText = refreshBtn.textContent;
    refreshBtn.textContent = networkScan ? '🔍 Network Scanning...' : '🔄 Refreshing...';
    
    try {
        // Start progress tracking for network scans
        if (networkScan) {
            startScanProgress('refresh');
        }
        
        const result = await client.refreshDevices({ networkScan, timeout: networkScan ? 15 : 10 });
        
        if (!networkScan) {
            // For non-network refresh, load devices immediately
            await loadDevices();
            showStatus(`Refreshed! Found ${result.count} device(s)`, 'success');
        }
        // For network scans, progress tracking will handle completion
        
    } catch (error) {
        if (networkScan) {
            stopScanProgress();
        }
        showStatus(`Error refreshing devices: ${error.message}`, 'error');
    } finally {
        refreshBtn.disabled = false;
        refreshBtn.textContent = originalText;
    }
}

async function triggerNetworkScan() {
    // Check if already scanning
    if (isScanning) {
        showStatus('Scan already in progress', 'info');
        return;
    }
    
    try {
        startScanProgress('network');
        showStatus('Starting comprehensive network scan...', 'info');
        
        const result = await client.triggerNetworkScan(20);
        
        // Progress tracking will handle completion automatically
        
    } catch (error) {
        stopScanProgress();
        showStatus(`Network scan error: ${error.message}`, 'error');
    }
}

// Validate network range
async function validateNetwork() {
    const networkInput = document.getElementById('networkRange').value.trim();
    const resultEl = document.getElementById('networkValidationResult');
    const startBtn = document.getElementById('startCustomScanBtn');
    
    if (!networkInput) {
        resultEl.innerHTML = '';
        startBtn.disabled = true;
        return;
    }
    
    try {
        resultEl.innerHTML = '<div class="validation-result">🔍 Validating network range...</div>';
        
        const result = await client.validateNetwork(networkInput);
        
        if (result.valid) {
            lastValidatedNetwork = result.normalized;
            const info = result.info;
            
            resultEl.innerHTML = `
                <div class="validation-result validation-success">
                    ✅ Valid network range!
                    <div class="network-info">
                        <div class="network-info-item">
                            <span class="network-info-label">Normalized:</span>
                            <span class="network-info-value">${result.normalized}</span>
                        </div>
                        <div class="network-info-item">
                            <span class="network-info-label">Network:</span>
                            <span class="network-info-value">${info.network_address}</span>
                        </div>
                        <div class="network-info-item">
                            <span class="network-info-label">Hosts to scan:</span>
                            <span class="network-info-value">${info.host_count}</span>
                        </div>
                        ${info.host_count > 1 ? `
                        <div class="network-info-item">
                            <span class="network-info-label">IP range:</span>
                            <span class="network-info-value">${info.first_host} - ${info.last_host}</span>
                        </div>` : ''}
                        <div class="network-info-item">
                            <span class="network-info-label">Est. scan time:</span>
                            <span class="network-info-value">${info.estimated_scan_time}</span>
                        </div>
                        ${info.host_count > 100 ? '<div style="margin-top: 10px; color: #f56565; font-size: 0.8rem;">⚠️ Large network - scan may take a while</div>' : ''}
                    </div>
                </div>
            `;
            startBtn.disabled = false;
        }
    } catch (error) {
        resultEl.innerHTML = `
            <div class="validation-result validation-error">
                ❌ Invalid network range<br>
                <strong>Error:</strong> ${error.message}
            </div>
        `;
        startBtn.disabled = true;
        lastValidatedNetwork = null;
    }
}

// Start custom network scan
async function startCustomNetworkScan() {
    if (!lastValidatedNetwork) {
        showStatus('Please validate the network range first', 'error');
        return;
    }
    
    // Check if already scanning
    if (isScanning) {
        showStatus('Scan already in progress', 'info');
        return;
    }
    
    const timeout = parseInt(document.getElementById('scanTimeout').value);
    
    try {
        closeCustomNetworkModal();
        startScanProgress('custom');
        showStatus(`Starting custom network scan: ${lastValidatedNetwork}`, 'info');
        
        const result = await client.triggerNetworkScan(timeout, lastValidatedNetwork);
        
        // Progress tracking will handle completion automatically
        
    } catch (error) {
        stopScanProgress();
        showStatus(`Custom network scan error: ${error.message}`, 'error');
    }
}

// Scan progress management functions
function startScanProgress(scanType = 'network') {
    isScanning = true;
    
    // Show progress section
    const progressSection = document.getElementById('scanProgressSection');
    const controlGroup = document.querySelector('.control-group');
    
    progressSection.style.display = 'block';
    controlGroup.classList.add('controls-disabled');
    
    // Update title based on scan type
    const title = document.getElementById('scanProgressTitle');
    switch (scanType) {
        case 'network':
            title.textContent = '🔍 Network Scan in Progress';
            break;
        case 'custom':
            title.textContent = '🌐 Custom Network Scan in Progress';
            break;
        case 'refresh':
            title.textContent = '🔄 Device Refresh in Progress';
            break;
        default:
            title.textContent = '⏳ Scan in Progress';
    }
    
    // Start polling for progress updates
    startProgressPolling();
}

function stopScanProgress() {
    isScanning = false;
    
    // Hide progress section
    const progressSection = document.getElementById('scanProgressSection');
    const controlGroup = document.querySelector('.control-group');
    
    progressSection.style.display = 'none';
    controlGroup.classList.remove('controls-disabled');
    
    // Stop polling
    stopProgressPolling();
    
    // Reset progress indicators
    resetProgressIndicators();
}

function startProgressPolling() {
    if (scanProgressInterval) {
        clearInterval(scanProgressInterval);
    }
    
    scanProgressInterval = setInterval(async () => {
        try {
            const progress = await client.getScanProgress();
            updateProgressDisplay(progress);
            
            // If scan is completed, stop polling
            if (!progress.is_scanning) {
                stopScanProgress();
                
                // Refresh device list after scan completes
                if (progress.progress_percent === 100) {
                    setTimeout(() => {
                        loadDevices();
                        showStatus(`🎉 Scan completed! Found ${progress.devices_found} device(s)`, 'success');
                    }, 1000);
                }
            }
        } catch (error) {
            console.error('Error fetching scan progress:', error);
            // Stop polling on error
            stopScanProgress();
            showStatus('Error monitoring scan progress', 'error');
        }
    }, 1000); // Poll every second
}

// Periodic Device Status Monitoring Functions
function startStatusPolling() {
    if (!isStatusPollingEnabled) return;
    
    // Clear any existing interval
    if (statusPollingInterval) {
        clearInterval(statusPollingInterval);
    }
    
    // Start polling at the configured frequency
    statusPollingInterval = setInterval(async () => {
        try {
            await updateDeviceStatuses();
        } catch (error) {
            console.warn('Status polling error:', error);
            // Don't show status errors unless critical
        }
    }, statusPollingFrequency * 1000);
    
    // Also update immediately if devices exist
    if (devices.length > 0) {
        updateDeviceStatuses();
    }
}

function stopStatusPolling() {
    if (statusPollingInterval) {
        clearInterval(statusPollingInterval);
        statusPollingInterval = null;
    }
}

async function updateDeviceStatuses() {
    if (devices.length === 0) return;
    
    try {
        const statusData = await client.getDevicesStatus();
        lastStatusUpdate = Date.now();
        
        // Update device states and connection indicators
        statusData.devices.forEach(deviceStatus => {
            const deviceCard = document.querySelector(`[data-udn="${escapeHtml(deviceStatus.udn)}"]`);
            if (deviceCard) {
                updateDeviceDisplay(deviceCard, deviceStatus);
                
                // Update global state tracking
                if (deviceStatus.state !== 'unknown') {
                    const numericState = deviceStatus.state === 'on' ? 1 : 0;
                    deviceStates.set(deviceStatus.udn, numericState);
                }
            }
        });
        
        // Update status indicator
        updateConnectionStatusIndicator(statusData.summary);
        
    } catch (error) {
        console.warn('Failed to update device statuses:', error);
        // Update status indicator to show connection issues
        updateConnectionStatusIndicator({ total: devices.length, online: 0, offline: devices.length, unknown: 0 });
    }
}

function updateDeviceDisplay(deviceCard, deviceStatus) {
    // Update state indicator
    const stateElement = deviceCard.querySelector('[data-state-indicator]');
    if (stateElement) {
        let stateClass, stateText, connectionClass = '';
        
        switch (deviceStatus.state) {
            case 'on':
                stateClass = 'state-on';
                stateText = 'ON';
                break;
            case 'off':
                stateClass = 'state-off';
                stateText = 'OFF';
                break;
            default:
                stateClass = 'state-unknown';
                stateText = 'UNKNOWN';
        }
        
        // Add connection status class
        switch (deviceStatus.connection_status) {
            case 'online':
                connectionClass = 'device-online';
                break;
            case 'offline':
                connectionClass = 'device-offline';
                stateText += ' (OFFLINE)';
                break;
            default:
                connectionClass = 'device-unknown';
        }
        
        stateElement.className = `device-state ${stateClass} ${connectionClass}`;
        stateElement.innerHTML = `
            <div class="state-indicator"></div>
            ${stateText}
        `;
        
        // Add title attribute with last update info
        const lastSeen = deviceStatus.last_seen ? new Date(deviceStatus.last_seen * 1000).toLocaleTimeString() : 'Unknown';
        stateElement.title = `Connection: ${deviceStatus.connection_status}\nLast seen: ${lastSeen}`;
    }
    
    // Add visual indication of connection status to the card
    deviceCard.classList.remove('card-online', 'card-offline', 'card-unknown');
    deviceCard.classList.add(`card-${deviceStatus.connection_status}`);
}

function updateConnectionStatusIndicator(summary) {
    const indicator = document.getElementById('connectionStatusIndicator');
    if (!indicator) return;
    
    const total = summary.total;
    const online = summary.online;
    const offline = summary.offline;
    
    let statusClass, statusText, statusIcon;
    
    if (total === 0) {
        statusClass = 'status-empty';
        statusIcon = '📱';
        statusText = 'No devices';
    } else if (online === total) {
        statusClass = 'status-all-online';
        statusIcon = '🟢';
        statusText = `All devices online (${total})`;
    } else if (online === 0) {
        statusClass = 'status-all-offline';
        statusIcon = '🔴';
        statusText = `All devices offline (${total})`;
    } else {
        statusClass = 'status-mixed';
        statusIcon = '🟡';
        statusText = `${online}/${total} devices online`;
    }
    
    indicator.className = `connection-status ${statusClass}`;
    indicator.innerHTML = `
        <span class="status-icon">${statusIcon}</span>
        <span class="status-text">${statusText}</span>
        ${lastStatusUpdate ? `<span class="status-time">Updated: ${new Date(lastStatusUpdate).toLocaleTimeString()}</span>` : ''}
    `;
}

// Settings Management
function toggleStatusPolling() {
    isStatusPollingEnabled = !isStatusPollingEnabled;
    localStorage.setItem('statusPollingEnabled', isStatusPollingEnabled.toString());
    
    if (isStatusPollingEnabled) {
        startStatusPolling();
        showStatus(`🔄 Auto-refresh enabled (every ${statusPollingFrequency}s)`, 'success');
    } else {
        stopStatusPolling();
        showStatus('⏸️ Auto-refresh disabled', 'info');
    }
    
    updateStatusPollingButton();
}

function updateStatusPollingFrequency(newFrequency) {
    statusPollingFrequency = Math.max(5, Math.min(300, parseInt(newFrequency) || 30)); // Between 5s and 5min
    localStorage.setItem('statusPollingFrequency', statusPollingFrequency.toString());
    
    // Restart polling with new frequency if it's currently enabled
    if (isStatusPollingEnabled) {
        startStatusPolling();
        showStatus(`🕒 Auto-refresh interval updated to ${statusPollingFrequency}s`, 'success');
    }
    
    // Update the input field
    const frequencyInput = document.getElementById('statusPollingFrequency');
    if (frequencyInput) {
        frequencyInput.value = statusPollingFrequency;
    }
}

function updateStatusPollingButton() {
    const button = document.getElementById('toggleStatusPollingBtn');
    if (button) {
        if (isStatusPollingEnabled) {
            button.textContent = '⏸️ Disable Auto-Refresh';
            button.className = 'btn btn-secondary';
        } else {
            button.textContent = '🔄 Enable Auto-Refresh';
            button.className = 'btn btn-success';
        }
    }
}

function stopProgressPolling() {
    if (scanProgressInterval) {
        clearInterval(scanProgressInterval);
        scanProgressInterval = null;
    }
}

function updateProgressDisplay(progress) {
    // Update progress bar
    const progressFill = document.getElementById('progressBarFill');
    const progressText = document.getElementById('progressBarText');
    
    progressFill.style.width = `${progress.progress_percent}%`;
    progressText.textContent = `${Math.round(progress.progress_percent)}%`;
    
    // Update current step
    document.getElementById('scanCurrentStep').textContent = progress.current_step;
    
    // Update network range
    document.getElementById('scanNetworkRange').textContent = progress.network_range || '-';
    
    // Update IP progress
    document.getElementById('scanIpsProgress').textContent = `${progress.ips_scanned} / ${progress.total_ips} IPs`;
    
    // Update devices found
    document.getElementById('scanDevicesFound').textContent = `${progress.devices_found} device${progress.devices_found !== 1 ? 's' : ''}`;
    
    // Update elapsed time
    document.getElementById('scanElapsedTime').textContent = progress.elapsed_time_formatted || '0s';
    
    // Update estimated time
    document.getElementById('scanEstimatedTime').textContent = progress.estimated_time_remaining_formatted || '-';
    
    // Update cancel button state
    const cancelBtn = document.getElementById('cancelScanBtn');
    cancelBtn.disabled = !progress.can_cancel;
}

function resetProgressIndicators() {
    document.getElementById('progressBarFill').style.width = '0%';
    document.getElementById('progressBarText').textContent = '0%';
    document.getElementById('scanCurrentStep').textContent = 'Starting scan...';
    document.getElementById('scanNetworkRange').textContent = '-';
    document.getElementById('scanIpsProgress').textContent = '0 / 0 IPs';
    document.getElementById('scanDevicesFound').textContent = '0 devices';
    document.getElementById('scanElapsedTime').textContent = '0s';
    document.getElementById('scanEstimatedTime').textContent = '-';
}

// Cancel scan function
async function cancelCurrentScan() {
    try {
        const result = await client.cancelScan();
        showStatus('🛑 Scan cancelled', 'info');
    } catch (error) {
        showStatus(`Error cancelling scan: ${error.message}`, 'error');
    }
}

// Bulk device control functions
async function turnAllDevicesOn() {
    const deviceCount = devices.length;
    
    if (deviceCount === 0) {
        showStatus('No devices available to turn on', 'info');
        return;
    }
    
    if (!confirm(`Turn ON all ${deviceCount} device(s)?\n\nThis will attempt to turn on every discovered WeMo device.`)) {
        return;
    }
    
    // Disable bulk control buttons during operation
    const turnOnBtn = document.getElementById('turnAllOnBtn');
    const turnOffBtn = document.getElementById('turnAllOffBtn');
    const originalOnText = turnOnBtn.textContent;
    const originalOffText = turnOffBtn.textContent;
    
    turnOnBtn.disabled = true;
    turnOffBtn.disabled = true;
    turnOnBtn.textContent = '⏳ Turning On...';
    
    try {
        showStatus(`🟢 Turning on all ${deviceCount} devices...`, 'info');
        const result = await client.turnAllDevicesOn();
        
        const summary = result.summary;
        const successEmoji = summary.successful > 0 ? '🎉' : '🤔';
        
        let statusMessage = `${successEmoji} Bulk Turn ON completed: ${summary.successful} successful`;
        if (summary.failed > 0) {
            statusMessage += `, ${summary.failed} failed`;
        }
        if (summary.skipped > 0) {
            statusMessage += `, ${summary.skipped} skipped`;
        }
        
        const statusType = summary.successful > 0 ? 'success' : summary.failed > 0 ? 'error' : 'info';
        showStatus(statusMessage, statusType);
        
        // Show detailed results in console for debugging
        console.log('Bulk turn on results:', result);
        
        // Refresh device states after a short delay
        setTimeout(async () => {
            try {
                await refreshDeviceStates();
            } catch (error) {
                console.warn('Failed to refresh device states after bulk operation:', error);
            }
        }, 1000);
        
    } catch (error) {
        showStatus(`Error turning on devices: ${error.message}`, 'error');
        console.error('Bulk turn on error:', error);
    } finally {
        // Re-enable buttons
        turnOnBtn.disabled = false;
        turnOffBtn.disabled = false;
        turnOnBtn.textContent = originalOnText;
    }
}

async function turnAllDevicesOff() {
    const deviceCount = devices.length;
    
    if (deviceCount === 0) {
        showStatus('No devices available to turn off', 'info');
        return;
    }
    
    if (!confirm(`Turn OFF all ${deviceCount} device(s)?\n\nThis will attempt to turn off every discovered WeMo device.`)) {
        return;
    }
    
    // Disable bulk control buttons during operation
    const turnOnBtn = document.getElementById('turnAllOnBtn');
    const turnOffBtn = document.getElementById('turnAllOffBtn');
    const originalOnText = turnOnBtn.textContent;
    const originalOffText = turnOffBtn.textContent;
    
    turnOnBtn.disabled = true;
    turnOffBtn.disabled = true;
    turnOffBtn.textContent = '⏳ Turning Off...';
    
    try {
        showStatus(`🔴 Turning off all ${deviceCount} devices...`, 'info');
        const result = await client.turnAllDevicesOff();
        
        const summary = result.summary;
        const successEmoji = summary.successful > 0 ? '🎉' : '🤔';
        
        let statusMessage = `${successEmoji} Bulk Turn OFF completed: ${summary.successful} successful`;
        if (summary.failed > 0) {
            statusMessage += `, ${summary.failed} failed`;
        }
        if (summary.skipped > 0) {
            statusMessage += `, ${summary.skipped} skipped`;
        }
        
        const statusType = summary.successful > 0 ? 'success' : summary.failed > 0 ? 'error' : 'info';
        showStatus(statusMessage, statusType);
        
        // Show detailed results in console for debugging
        console.log('Bulk turn off results:', result);
        
        // Refresh device states after a short delay
        setTimeout(async () => {
            try {
                await refreshDeviceStates();
            } catch (error) {
                console.warn('Failed to refresh device states after bulk operation:', error);
            }
        }, 1000);
        
    } catch (error) {
        showStatus(`Error turning off devices: ${error.message}`, 'error');
        console.error('Bulk turn off error:', error);
    } finally {
        // Re-enable buttons
        turnOnBtn.disabled = false;
        turnOffBtn.disabled = false;
        turnOffBtn.textContent = originalOffText;
    }
}

// Helper function to refresh device states
async function refreshDeviceStates() {
    if (!devices || devices.length === 0) return;
    
    const statePromises = devices.map(async (device) => {
        try {
            const result = await client.callDeviceMethod(device.udn, 'get_state');
            updateDeviceStateIndicator(device.udn, result.result);
        } catch (error) {
            console.warn(`Failed to refresh state for device ${device.name}:`, error);
        }
    });
    
    await Promise.allSettled(statePromises);
}

async function updateDiscoveryStatus() {
    try {
        const status = await client.getDiscoveryStatus();
        const statusEl = document.getElementById('discoveryStatus');
        if (statusEl) {
            statusEl.innerHTML = `
                <small>
                    Auto-discovery: ${status.auto_discovery_enabled ? '✅ Enabled' : '❌ Disabled'} |
                    Last scan: ${status.last_discovery_formatted || 'Never'} |
                    Total scans: ${status.discovery_count}
                </small>
            `;
        }
    } catch (error) {
        console.error('Failed to update discovery status:', error);
    }
}

// Event listeners
refreshBtn.addEventListener('click', () => refreshDevices(false));
document.getElementById('networkScanBtn').addEventListener('click', triggerNetworkScan);
customNetworkScanBtn.addEventListener('click', () => showModal(customNetworkModal));
addDeviceBtn.addEventListener('click', () => showModal(addDeviceModal));
document.getElementById('forgetAllBtn').addEventListener('click', forgetAllDevices);

// Add device form (supports multiple IP addresses)
document.getElementById('addDeviceForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const ip = document.getElementById('deviceIP').value.trim();
    if (!ip) return;
    
    try {
        // Show appropriate loading message for single vs multiple IPs
        const ipList = ip.split(/[\s,;]+/).filter(ip => ip.trim());
        if (ipList.length === 1) {
            showStatus('Adding device...', 'info');
        } else {
            showStatus(`Adding ${ipList.length} devices...`, 'info');
        }
        
        const result = await client.discoverDeviceByIP(ip);
        
        closeModal();
        document.getElementById('deviceIP').value = '';
        
        // Handle the response based on whether it's single or multiple devices
        if (result.results) {
            // Multiple device response
            const { total_ips_processed, newly_discovered, already_existed, failed, summary } = result;
            
            if (newly_discovered > 0) {
                await loadDevices();
            }
            
            // Generate detailed status message
            let statusType = 'success';
            let statusMessage = `✅ ${summary}`;
            
            if (failed > 0 && newly_discovered === 0) {
                statusType = 'error';
                statusMessage = `❌ ${summary}`;
            } else if (failed > 0) {
                statusType = 'info';
                statusMessage = `⚠️ ${summary}`;
            }
            
            showStatus(statusMessage, statusType);
            
            // Show detailed results in console for debugging
            console.log('Device discovery results:', result.results);
            
            // If there were failures, show additional details
            if (failed > 0) {
                const failedDevices = result.results.filter(r => !r.success);
                console.warn('Failed device discoveries:', failedDevices);
                
                setTimeout(() => {
                    const failedIPs = failedDevices.map(r => r.ip).join(', ');
                    showStatus(`Failed to discover devices at: ${failedIPs}`, 'error');
                }, 2000);
            }
        } else {
            // Legacy single device response (backward compatibility)
            if (result.already_discovered) {
                showStatus(`Device "${result.name}" was already discovered!`, 'info');
            } else {
                showStatus(`Device "${result.name}" added successfully!`, 'success');
                await loadDevices();
            }
        }
        
    } catch (error) {
        showStatus(`Error adding device(s): ${error.message}`, 'error');
        console.error('Device discovery error:', error);
    }
});

// Method execution form
document.getElementById('methodArgsForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const argsInput = document.getElementById('methodArgs').value.trim();
    const kwargsInput = document.getElementById('methodKwargs').value.trim();
    const resultEl = document.getElementById('methodResult');
    
    let args, kwargs;
    
    try {
        args = JSON.parse(argsInput || '[]');
        kwargs = JSON.parse(kwargsInput || '{}');
    } catch (parseError) {
        resultEl.innerHTML = `<div class="method-result error">Invalid JSON format: ${parseError.message}</div>`;
        return;
    }
    
    try {
        resultEl.innerHTML = '<div class="method-result">Executing method...</div>';
        
        const result = await client.callDeviceMethod(currentDevice.udn, currentMethod, args, kwargs);
        
        // Handle state updates for state-related methods
        if (currentMethod === 'get_state') {
            const state = result.result;
            updateDeviceStateIndicator(currentDevice.udn, state);
            const stateText = state === 1 ? 'ON' : state === 0 ? 'OFF' : 'UNKNOWN';
            const stateEmoji = state === 1 ? '🟢' : state === 0 ? '🔴' : '🟡';
            showStatus(`${stateEmoji} Device state: ${stateText}`, 'success');
        } else if (currentMethod === 'toggle' || currentMethod === 'on' || currentMethod === 'off') {
            // Auto-refresh state after state-changing operations
            setTimeout(async () => {
                try {
                    const stateResult = await client.callDeviceMethod(currentDevice.udn, 'get_state');
                    updateDeviceStateIndicator(currentDevice.udn, stateResult.result);
                } catch (stateError) {
                    console.warn('Failed to refresh state after method execution:', stateError);
                }
            }, 500);
        }
        
        resultEl.innerHTML = `
            <div class="method-result success">
                <strong>Success!</strong><br>
                ${JSON.stringify(result, null, 2)}
            </div>
        `;
        
        showStatus(`Method "${currentMethod}" executed successfully!`, 'success');
        
    } catch (error) {
        resultEl.innerHTML = `
            <div class="method-result error">
                <strong>Error:</strong><br>
                ${error.message}
            </div>
        `;
        
        showStatus(`Error executing method: ${error.message}`, 'error');
    }
});

// Custom network scan form event listeners
document.getElementById('validateNetworkBtn').addEventListener('click', validateNetwork);
document.getElementById('customNetworkForm').addEventListener('submit', (e) => {
    e.preventDefault();
    startCustomNetworkScan();
});

// Cancel scan event listener
document.getElementById('cancelScanBtn').addEventListener('click', cancelCurrentScan);

// Bulk control event listeners
document.getElementById('turnAllOnBtn').addEventListener('click', turnAllDevicesOn);
document.getElementById('turnAllOffBtn').addEventListener('click', turnAllDevicesOff);

// Status monitoring event listeners
document.getElementById('toggleStatusPollingBtn').addEventListener('click', toggleStatusPolling);
document.getElementById('manualRefreshStatusBtn').addEventListener('click', () => {
    if (devices.length > 0) {
        updateDeviceStatuses();
        showStatus('🔄 Device status updated manually', 'success');
    } else {
        showStatus('No devices available to update', 'info');
    }
});
document.getElementById('statusPollingFrequency').addEventListener('change', (e) => {
    updateStatusPollingFrequency(e.target.value);
});


// Auto-validate when user types (with debounce)
let networkValidationTimeout;
document.getElementById('networkRange').addEventListener('input', () => {
    clearTimeout(networkValidationTimeout);
    networkValidationTimeout = setTimeout(() => {
        const value = document.getElementById('networkRange').value.trim();
        if (value && value.length > 3) {
            validateNetwork();
        } else {
            document.getElementById('networkValidationResult').innerHTML = '';
            document.getElementById('startCustomScanBtn').disabled = true;
            lastValidatedNetwork = null;
        }
    }, 500); // 500ms debounce
});

// Modal event listeners
window.onclick = function(event) {
    if (event.target === addDeviceModal) {
        closeModal();
    } else if (event.target === customNetworkModal) {
        closeCustomNetworkModal();
    } else if (event.target === methodModal) {
        closeMethodModal();
    } else if (event.target === argsModal) {
        closeArgsModal();
    }
};

// Close button event listeners
document.querySelectorAll('.close').forEach(closeBtn => {
    closeBtn.onclick = function() {
        const modal = this.closest('.modal');
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    };
});

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeModal();
        closeCustomNetworkModal();
        closeMethodModal();
        closeArgsModal();
    }
});

// Initialize the app
document.addEventListener('DOMContentLoaded', () => {
    // Initialize theme first
    initializeTheme();
    
    // Initialize clock
    initializeClock();
    
    loadDevices();
    updateDiscoveryStatus();
    updateStatusPollingButton();
    
    // Initialize frequency input field
    const frequencyInput = document.getElementById('statusPollingFrequency');
    if (frequencyInput) {
        frequencyInput.value = statusPollingFrequency;
    }
    
    showStatus('PyWemo Web Interface loaded successfully!', 'success');
    
    // Update discovery status every 30 seconds
    setInterval(updateDiscoveryStatus, 30000);
    
    // Start status polling if enabled
    if (isStatusPollingEnabled) {
        setTimeout(startStatusPolling, 2000); // Small delay after initial load
    }
});

// Auto-refresh devices every 5 minutes (only if status polling is disabled)
setInterval(() => {
    if (!isStatusPollingEnabled) {
        loadDevices();
    }
}, 5 * 60 * 1000);

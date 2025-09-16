// Quick Status Polling Diagnostics Script
// Paste this in your browser console on http://localhost:5000

console.log('=== STATUS POLLING DIAGNOSTICS ===');

console.log('🔍 Checking status polling configuration...');
console.log('isStatusPollingEnabled:', typeof isStatusPollingEnabled !== 'undefined' ? isStatusPollingEnabled : 'UNDEFINED');
console.log('statusPollingFrequency:', typeof statusPollingFrequency !== 'undefined' ? statusPollingFrequency : 'UNDEFINED');
console.log('statusPollingInterval:', typeof statusPollingInterval !== 'undefined' ? statusPollingInterval : 'UNDEFINED');

console.log('🔍 Checking localStorage values...');
console.log('localStorage statusPollingEnabled:', localStorage.getItem('statusPollingEnabled'));
console.log('localStorage statusPollingFrequency:', localStorage.getItem('statusPollingFrequency'));

console.log('🔍 Checking DOM elements...');
const toggleBtn = document.getElementById('toggleStatusPollingBtn');
const frequencyInput = document.getElementById('statusPollingFrequency');
const refreshBtn = document.getElementById('manualRefreshStatusBtn');

console.log('Toggle button exists:', !!toggleBtn);
if (toggleBtn) console.log('Toggle button text:', toggleBtn.textContent);

console.log('Frequency input exists:', !!frequencyInput);
if (frequencyInput) console.log('Frequency input value:', frequencyInput.value);

console.log('Manual refresh button exists:', !!refreshBtn);

console.log('🔍 Current device count:', typeof devices !== 'undefined' ? devices.length : 'DEVICES UNDEFINED');

console.log('=== ENABLING STATUS POLLING FOR TEST ===');

function enableStatusPollingTest() {
    console.log('🚀 Attempting to enable status polling...');
    
    if (typeof toggleStatusPolling === 'function') {
        // Check current state and enable if disabled
        if (!isStatusPollingEnabled) {
            console.log('📞 Calling toggleStatusPolling()...');
            toggleStatusPolling();
        } else {
            console.log('✅ Status polling is already enabled');
        }
    } else {
        console.log('❌ toggleStatusPolling function not found, manually enabling...');
        localStorage.setItem('statusPollingEnabled', 'true');
        location.reload();
    }
    
    setTimeout(() => {
        console.log('🔍 Post-enable check:');
        console.log('isStatusPollingEnabled:', isStatusPollingEnabled);
        console.log('statusPollingInterval:', statusPollingInterval);
        if (toggleBtn) console.log('Toggle button text:', toggleBtn.textContent);
    }, 1000);
}

function manualStatusUpdate() {
    console.log('🔄 Running manual status update...');
    if (typeof updateDeviceStatuses === 'function') {
        updateDeviceStatuses().then(() => {
            console.log('✅ Manual status update completed');
        }).catch(err => {
            console.log('❌ Manual status update failed:', err);
        });
    } else {
        console.log('❌ updateDeviceStatuses function not found');
    }
}

// Make functions available globally
window.enableStatusPollingTest = enableStatusPollingTest;
window.manualStatusUpdate = manualStatusUpdate;

console.log('=== INSTRUCTIONS ===');
console.log('1. Run: enableStatusPollingTest() - to enable automatic polling');
console.log('2. Run: manualStatusUpdate() - to trigger immediate update');
console.log('3. Press physical buttons on WeMo devices');
console.log('4. Wait 30 seconds to see if UI updates automatically');
// Diagnostic script to test real-time status monitoring
// This script can be run in the browser console to debug the issue

console.log('🔍 PyWemo Status Monitoring Diagnostics');
console.log('==========================================');

// Test 1: Check if client is available
console.log('1. Testing API client...');
if (typeof client !== 'undefined') {
    console.log('✅ API client is available');
} else {
    console.log('❌ API client not found');
    return;
}

// Test 2: Check if status polling is enabled
console.log('2. Checking status polling configuration...');
console.log(`   Status Polling Enabled: ${isStatusPollingEnabled}`);
console.log(`   Polling Frequency: ${statusPollingFrequency} seconds`);
console.log(`   Status Polling Interval: ${statusPollingInterval ? 'Running' : 'Stopped'}`);

// Test 3: Test manual API call
console.log('3. Testing manual API call to /devices/status...');
client.getDevicesStatus().then(statusData => {
    console.log('✅ API call successful');
    console.log('   Device count:', statusData.devices.length);
    console.log('   Summary:', statusData.summary);
    console.log('   Sample device:', statusData.devices[0]);
    
    // Test 4: Check if device cards exist
    console.log('4. Checking device card elements...');
    statusData.devices.forEach((deviceStatus, index) => {
        const selector = `[data-udn="${deviceStatus.udn}"]`;
        const deviceCard = document.querySelector(selector);
        
        if (deviceCard) {
            console.log(`✅ Device ${index + 1}: Card found`);
            console.log(`   Name: ${deviceStatus.name}`);
            console.log(`   UDN: ${deviceStatus.udn}`);
            console.log(`   State: ${deviceStatus.state}`);
            console.log(`   Connection: ${deviceStatus.connection_status}`);
            
            // Check state indicator
            const stateElement = deviceCard.querySelector('[data-state-indicator]');
            if (stateElement) {
                console.log(`   State indicator: Found`);
                console.log(`   Current text: "${stateElement.textContent.trim()}"`);
                console.log(`   Current classes: "${stateElement.className}"`);
                
                // Test manual update
                console.log('   Testing manual state update...');
                try {
                    updateDeviceDisplay(deviceCard, deviceStatus);
                    console.log('   ✅ Manual update successful');
                    console.log(`   New text: "${stateElement.textContent.trim()}"`);
                    console.log(`   New classes: "${stateElement.className}"`);
                } catch (error) {
                    console.log(`   ❌ Manual update failed: ${error.message}`);
                }
            } else {
                console.log(`   ❌ State indicator not found`);
            }
        } else {
            console.log(`❌ Device ${index + 1}: Card NOT found for selector: ${selector}`);
        }
    });
    
    // Test 5: Check connection status indicator
    console.log('5. Testing connection status indicator...');
    const connectionIndicator = document.getElementById('connectionStatusIndicator');
    if (connectionIndicator) {
        console.log('✅ Connection status indicator found');
        console.log(`   Current content: "${connectionIndicator.textContent.trim()}"`);
        
        // Test manual update
        try {
            updateConnectionStatusIndicator(statusData.summary);
            console.log('✅ Connection indicator update successful');
            console.log(`   New content: "${connectionIndicator.textContent.trim()}"`);
        } catch (error) {
            console.log(`❌ Connection indicator update failed: ${error.message}`);
        }
    } else {
        console.log('❌ Connection status indicator not found');
    }
    
}).catch(error => {
    console.log('❌ API call failed:', error.message);
});

// Test 6: Enable status polling for testing
console.log('6. Testing status polling controls...');
const toggleButton = document.getElementById('toggleStatusPollingBtn');
if (toggleButton) {
    console.log('✅ Toggle button found');
    console.log(`   Button text: "${toggleButton.textContent.trim()}"`);
    console.log(`   Button classes: "${toggleButton.className}"`);
} else {
    console.log('❌ Toggle button not found');
}

const frequencyInput = document.getElementById('statusPollingFrequency');
if (frequencyInput) {
    console.log('✅ Frequency input found');
    console.log(`   Current value: ${frequencyInput.value}`);
} else {
    console.log('❌ Frequency input not found');
}

// Helper function to enable status polling for testing
window.enableStatusPollingTest = function() {
    console.log('🔄 Enabling status polling for testing...');
    isStatusPollingEnabled = true;
    localStorage.setItem('statusPollingEnabled', 'true');
    updateStatusPollingButton();
    startStatusPolling();
    console.log('✅ Status polling enabled');
    console.log('   Watch for automatic updates every 30 seconds...');
};

// Helper function to manually trigger status update
window.manualStatusUpdate = function() {
    console.log('🔄 Triggering manual status update...');
    updateDeviceStatuses().then(() => {
        console.log('✅ Manual status update completed');
    }).catch(error => {
        console.log('❌ Manual status update failed:', error.message);
    });
};

console.log('');
console.log('📋 Next Steps:');
console.log('1. Run: enableStatusPollingTest() - to enable automatic polling');
console.log('2. Run: manualStatusUpdate() - to trigger immediate update');
console.log('3. Press physical button on a device');
console.log('4. Wait 30 seconds or run manualStatusUpdate() to see changes');
console.log('');
console.log('🎯 If state changes are not reflected in UI after following steps,');
console.log('   there is an issue with the updateDeviceDisplay function.');
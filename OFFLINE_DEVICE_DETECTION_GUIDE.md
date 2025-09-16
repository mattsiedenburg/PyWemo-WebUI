# 🔴 Offline Device Detection System

## 📋 **Current System Overview**

Your PyWemo API **already has comprehensive offline device detection** implemented! Here's how it works:

### ✅ **What's Already Working:**

#### **1. Backend Detection Logic:**
```python
# In get_device_status_info() function:
try:
    state = device.get_state()  # Try to communicate with device
    device_info["connection_status"] = "online"
except Exception as e:
    device_info["connection_status"] = "offline"  # Mark as offline
    device_info["error"] = str(e)
```

#### **2. API Response Structure:**
```json
{
  "devices": [
    {
      "name": "Wemo Mini",
      "ip_address": "192.168.16.153",
      "state": "unknown",
      "connection_status": "offline",  ← OFFLINE DETECTION
      "last_seen": 1757869000.123,
      "error": "Connection timeout"
    }
  ],
  "summary": {
    "total": 3,
    "online": 2,   ← ONLINE COUNT
    "offline": 1,  ← OFFLINE COUNT  
    "unknown": 0
  }
}
```

#### **3. Web UI Visual Indicators:**

##### **Status Monitoring Section:**
- 🟢 **All online**: "All devices online (3)"
- 🔴 **All offline**: "All devices offline (3)"
- 🟡 **Mixed**: "2/3 devices online"

##### **Device Cards:**
- 🟢 **Online devices**: Green border, normal opacity
- 🔴 **Offline devices**: Red border, 70% opacity (dimmed)

##### **Device State Badges:**
- **Online**: "ON" / "OFF" (normal state)
- **Offline**: "OFF (OFFLINE)" with pulsing animation

#### **4. CSS Styling for Offline Devices:**
```css
.device-card.card-offline {
    border-left: 4px solid #f56565;  /* Red border */
    opacity: 0.7;                    /* Dimmed appearance */
}

.device-state.device-offline {
    background: rgba(245, 101, 101, 0.1);  /* Red background */
    color: #f56565;                         /* Red text */
}

.device-state.device-offline .state-indicator {
    animation: pulse-offline 2s infinite;   /* Pulsing animation */
}
```

---

## 🧪 **How to Test Offline Detection**

### **Method 1: Physical Test**
1. **Unplug** one WeMo device from power
2. **Wait** 30-60 seconds for next status check
3. **Check web UI** - device should show as offline:
   - Red border on device card
   - Dimmed (70% opacity) appearance
   - "OFF (OFFLINE)" status badge
   - Status summary shows "2/3 devices online"

### **Method 2: Network Test**  
1. **Block network access** to device (router settings)
2. **Wait** for next status polling cycle
3. **Observe** offline indicators in web UI

### **Method 3: Manual Status Check**
```bash
# Check current status via API
curl -s "http://localhost:5000/devices/status" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for device in data['devices']:
    status = device['connection_status']
    emoji = '🟢' if status == 'online' else '🔴'
    print(f'{emoji} {device[\"name\"]} - {status.upper()}')
"
```

---

## 🎨 **Current Visual Indicators**

### **Web UI Indicators:**
| Status | Device Card | Status Badge | Summary Icon |
|--------|-------------|--------------|--------------|
| Online | Green border, normal opacity | "ON"/"OFF" | 🟢 |
| Offline | Red border, 70% opacity | "OFF (OFFLINE)" | 🔴 |
| Mixed | Various | Various | 🟡 |

### **Status Monitoring Section:**
- Shows real-time connection statistics
- Updates every 15-30 seconds (if enabled)
- Color-coded indicators for quick status assessment

---

## 🚀 **Enhancement Suggestions**

If you want to improve the offline detection system, here are some ideas:

### **1. Enhanced Notifications**
```javascript
// Add to updateDeviceDisplay function:
if (deviceStatus.connection_status === 'offline' && !deviceStatus.wasOffline) {
    showNotification(`Device "${deviceStatus.name}" went offline`, 'warning');
}
```

### **2. Detailed Offline Information**
```javascript
// Show more offline details:
if (device.connection_status === 'offline') {
    const lastSeen = device.last_seen ? 
        new Date(device.last_seen * 1000).toLocaleString() : 'Unknown';
    tooltip += `\nLast seen: ${lastSeen}`;
    if (device.error) {
        tooltip += `\nError: ${device.error}`;
    }
}
```

### **3. Offline Device Management**
- **Auto-retry**: Attempt to reconnect offline devices
- **Ignore temporarily**: Mark devices as "maintenance mode"
- **Remove offline**: Option to remove persistently offline devices

### **4. Advanced Offline Detection**
```python
# Enhanced timeout and retry logic:
def check_device_connectivity(device, retries=3, timeout=5):
    for attempt in range(retries):
        try:
            # Try multiple methods to verify connectivity
            if hasattr(device, 'get_state'):
                device.get_state()
            elif hasattr(device, 'basicevent'):
                device.basicevent.GetFriendlyName()
            return 'online'
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)  # Wait before retry
                continue
            return 'offline', str(e)
```

### **5. Historical Offline Tracking**
```python
# Track offline history for reliability metrics:
device_info["offline_history"] = {
    "total_offline_events": count,
    "last_offline_duration": duration_seconds,
    "uptime_percentage": uptime_percent
}
```

---

## 📊 **Current Status Monitoring Features**

Your system already includes:

### **✅ Real-time Detection:**
- Parallel device checking (ThreadPoolExecutor)
- Configurable timeout (5 seconds default)  
- Multiple fallback detection methods
- Error message capture and display

### **✅ Web UI Integration:**
- Visual status indicators
- Connection status summary
- Individual device status
- Automatic UI updates (when status monitoring enabled)

### **✅ API Endpoints:**
- `/devices/status` - Get all device connection states
- Individual device state checking via method calls
- Detailed error information in API responses

---

## 🎯 **Summary**

**Your offline device detection system is already fully implemented and working!**

### **To see it in action:**
1. **Enable status monitoring** in web UI (click "Enable Auto-Refresh")
2. **Unplug a device** from power
3. **Wait 30 seconds** for next status check
4. **Observe** the visual changes:
   - Device card gets red border and dims
   - Status badge shows "OFF (OFFLINE)"
   - Summary shows "X/Y devices online"

### **Enhancement Options:**
If you want to enhance the system further, consider:
- Push notifications for offline events
- Historical offline tracking  
- Advanced retry logic
- Maintenance mode for expected outages
- Email/SMS alerts for critical devices

The foundation is solid - any enhancements would be additions to an already comprehensive system!

---

## 🔧 **Quick Verification Steps**

1. **Check if status monitoring is enabled:**
   - Open http://localhost:5000
   - Look for "⏸️ Disable Auto-Refresh" (means it's enabled)
   - If shows "🔄 Enable Auto-Refresh", click it to enable

2. **Test offline detection:**
   - Unplug one WeMo device  
   - Wait 30-60 seconds
   - Refresh page or wait for auto-refresh
   - Device should show offline indicators

3. **Verify API response:**
   ```bash
   curl "http://localhost:5000/devices/status" | grep -i offline
   ```

The system is ready to detect offline devices - you just need to trigger the condition to see it in action! 🎉
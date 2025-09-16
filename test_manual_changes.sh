#!/bin/bash
# Test script to verify manual device state change detection using curl

echo "🎯 Manual Device Change Detection Test"
echo "====================================================="

# Wait for API to be ready
echo "⏳ Waiting for PyWemo API to be ready..."
max_wait=180
wait_time=0

while [ $wait_time -lt $max_wait ]; do
    if curl -s http://localhost:5000/devices >/dev/null 2>&1; then
        device_count=$(curl -s http://localhost:5000/devices | python3 -c "import sys, json; data = json.load(sys.stdin); print(len(data))" 2>/dev/null)
        if [ "$device_count" -gt "0" ] 2>/dev/null; then
            echo "✅ API ready! Found $device_count devices"
            break
        else
            echo "⏳ API ready but no devices found yet..."
        fi
    else
        echo "⏳ Waiting for API..."
    fi
    sleep 10
    wait_time=$((wait_time + 10))
done

if [ $wait_time -ge $max_wait ]; then
    echo "❌ API not ready after 3 minutes. Please check if the container is running."
    echo "   Try: docker logs pywemo-status"
    exit 1
fi

echo ""
echo "🚀 Starting monitoring..."
echo "💡 Instructions:"
echo "   1. Leave this script running"
echo "   2. Walk to your WeMo devices"
echo "   3. Press the physical buttons"
echo "   4. Watch for changes to be detected here!"
echo ""
echo "🔄 Starting manual device change detection test..."
echo "📊 Polling every 15 seconds"
echo "👆 Press physical buttons on your WeMo devices to test detection"
echo "------------------------------------------------------------"

# Create a temporary file to store previous states
previous_states="/tmp/wemo_previous_states.json"
echo "{}" > "$previous_states"

polling_interval=15

while true; do
    timestamp=$(date "+%H:%M:%S")
    
    # Get current device states
    devices=$(curl -s http://localhost:5000/devices 2>/dev/null)
    
    if [ $? -ne 0 ] || [ -z "$devices" ]; then
        echo "[$timestamp] ❌ No devices found or API not ready"
        sleep $polling_interval
        continue
    fi
    
    # Create current states file
    current_states="/tmp/wemo_current_states.json"
    echo "{}" > "$current_states"
    
    # Get states for each device
    echo "$devices" | python3 -c "
import json, sys, urllib.request, urllib.error
devices = json.load(sys.stdin)
current_states = {}

for device in devices:
    udn = device['udn']
    name = device['name']
    
    # Get device state
    try:
        url = f'http://localhost:5000/device/{udn}/get_state'
        data = json.dumps({'args': [], 'kwargs': {}}).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        req.get_method = lambda: 'POST'
        
        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.load(response)
            state = result.get('result', 'unknown')
            state_text = 'ON' if state == 1 else 'OFF' if state == 0 else 'UNKNOWN'
            current_states[udn] = {'name': name, 'state': state_text}
    except Exception as e:
        current_states[udn] = {'name': name, 'state': 'OFFLINE', 'error': str(e)}

print(json.dumps(current_states, indent=2))
" > "$current_states" 2>/dev/null
    
    if [ ! -s "$current_states" ]; then
        echo "[$timestamp] ❌ Error getting device states"
        sleep $polling_interval
        continue
    fi
    
    # Compare with previous states
    changes_detected=false
    
    # Read current and previous states
    if [ -f "$previous_states" ] && [ -s "$previous_states" ]; then
        # Check for changes using python
        python3 -c "
import json
try:
    with open('$current_states', 'r') as f:
        current = json.load(f)
    with open('$previous_states', 'r') as f:
        previous = json.load(f)
    
    changes_found = False
    
    for udn, current_info in current.items():
        device_name = current_info['name']
        current_state = current_info['state']
        
        if udn in previous:
            previous_state = previous[udn]['state']
            if current_state != previous_state:
                print(f'CHANGE:{device_name}:{previous_state}:{current_state}')
                changes_found = True
        else:
            print(f'NEW:{device_name}:{current_state}')
    
    if not changes_found and previous:
        device_count = len(current)
        on_count = sum(1 for info in current.values() if info['state'] == 'ON')
        off_count = sum(1 for info in current.values() if info['state'] == 'OFF')
        print(f'STATUS:{device_count}:{on_count}:{off_count}')
    
except Exception as e:
    print(f'ERROR:{e}')
" | while IFS= read -r line; do
            if [[ "$line" == CHANGE:* ]]; then
                IFS=':' read -r _ device_name previous_state current_state <<< "$line"
                echo "[$timestamp] 🔄 CHANGE DETECTED: $device_name"
                echo "             └── $previous_state → $current_state"
                changes_detected=true
            elif [[ "$line" == NEW:* ]]; then
                IFS=':' read -r _ device_name current_state <<< "$line"
                echo "[$timestamp] 📱 Monitoring: $device_name ($current_state)"
            elif [[ "$line" == STATUS:* ]]; then
                IFS=':' read -r _ device_count on_count off_count <<< "$line"
                echo "[$timestamp] ✅ Monitoring $device_count devices: $on_count ON, $off_count OFF"
            elif [[ "$line" == ERROR:* ]]; then
                echo "[$timestamp] ❌ Error: ${line#ERROR:}"
            fi
        done
    else
        # First run, just list devices
        python3 -c "
import json
with open('$current_states', 'r') as f:
    current = json.load(f)
for udn, info in current.items():
    print(f'📱 Monitoring: {info[\"name\"]} ({info[\"state\"]})')
"
    fi
    
    # Copy current states to previous for next iteration
    cp "$current_states" "$previous_states"
    
    sleep $polling_interval
done
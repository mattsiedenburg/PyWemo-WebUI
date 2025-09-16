#!/bin/bash
# Simple Status Monitoring Test Script
# This tests the same API endpoint that the web UI uses

echo "🚀 Starting Status Monitoring Test"
echo "📡 Testing http://localhost:5000/devices/status"
echo "🔴 Press physical buttons on your WeMo devices between polls"
echo "🛑 Press Ctrl+C to stop monitoring"
echo ""

POLL_COUNT=0

while true; do
    POLL_COUNT=$((POLL_COUNT + 1))
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    
    echo "📊 Poll #$POLL_COUNT - $TIMESTAMP"
    
    # Get device status and format output
    RESPONSE=$(curl -s "http://localhost:5000/devices/status")
    
    if [ $? -eq 0 ]; then
        # Extract and display device states
        echo "$RESPONSE" | python3 -c "
import json
import sys

try:
    data = json.load(sys.stdin)
    
    summary = data['summary']
    print(f'   📊 Summary: {summary[\"total\"]} total, {summary[\"online\"]} online, {summary[\"offline\"]} offline')
    
    for device in data['devices']:
        state_emoji = '🟢' if device['state'] == 'on' else '🔴' if device['state'] == 'off' else '🟡'
        connection_emoji = '📶' if device['connection_status'] == 'online' else '📵'
        print(f'   {state_emoji}{connection_emoji} {device[\"name\"]} ({device[\"ip_address\"]}) - {device[\"state\"].upper()}')
        
except Exception as e:
    print(f'   ❌ Error parsing response: {e}')
    print(f'   Raw response: {sys.stdin.read()[:200]}...')
"
    else
        echo "   ❌ Failed to connect to API"
    fi
    
    echo "   ⏰ Waiting 15 seconds for next poll..."
    echo "--------------------------------------------------------------------------------"
    
    sleep 15
done
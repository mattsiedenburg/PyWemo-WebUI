#!/usr/bin/env python3
"""
Test Offline Device Detection

This script demonstrates how the system detects and handles offline devices.
It will simulate taking devices offline and show how the API responds.
"""

import requests
import time
import json
from datetime import datetime

API_BASE = "http://localhost:5000"

def get_device_status():
    """Get current device status"""
    try:
        response = requests.get(f"{API_BASE}/devices/status", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error getting device status: {e}")
        return None

def format_device_status(device):
    """Format device status for display"""
    connection_emoji = "🟢" if device["connection_status"] == "online" else "🔴" if device["connection_status"] == "offline" else "🟡"
    state_emoji = "🟢" if device["state"] == "on" else "🔴" if device["state"] == "off" else "🟡"
    
    status_text = f"{device['name']} ({device['ip_address']})"
    if device["connection_status"] == "offline":
        status_text += f" - ⚠️ OFFLINE"
        if "error" in device:
            status_text += f" ({device['error'][:50]}...)"
    else:
        status_text += f" - {device['state'].upper()}"
    
    return f"{connection_emoji} {status_text}"

def print_status_summary(status_data):
    """Print formatted status summary"""
    if not status_data:
        print("❌ No status data available")
        return
    
    timestamp = datetime.fromtimestamp(status_data['timestamp']).strftime('%H:%M:%S')
    summary = status_data['summary']
    
    print(f"\n📊 Device Status Summary [{timestamp}]:")
    print(f"   📱 Total: {summary['total']}")
    print(f"   🟢 Online: {summary['online']}")
    print(f"   🔴 Offline: {summary['offline']}")
    print(f"   🟡 Unknown: {summary['unknown']}")
    
    if summary['total'] > 0:
        online_percentage = (summary['online'] / summary['total']) * 100
        print(f"   📈 Online Rate: {online_percentage:.1f}%")
    
    print("\n🔍 Individual Device Status:")
    for device in status_data['devices']:
        print(f"   {format_device_status(device)}")

def test_offline_scenarios():
    """Test various offline scenarios"""
    print("🚀 Testing Offline Device Detection")
    print("=" * 60)
    
    # Test 1: Check current status
    print("\n📋 Test 1: Current Device Status")
    print("-" * 40)
    status = get_device_status()
    print_status_summary(status)
    
    # Test 2: Instructions for manual offline testing
    print("\n📋 Test 2: Manual Offline Testing Instructions")
    print("-" * 40)
    print("🔌 To test offline detection:")
    print("   1. Unplug one of your WeMo devices from power")
    print("   2. Wait 10 seconds")
    print("   3. Run this script again")
    print("   4. The unplugged device should show as OFFLINE")
    print("   5. Plug it back in and wait 30 seconds")
    print("   6. Run script again - device should be ONLINE")
    
    # Test 3: Check for any devices that are already offline
    if status and status['devices']:
        offline_devices = [d for d in status['devices'] if d['connection_status'] == 'offline']
        if offline_devices:
            print(f"\n⚠️  Currently {len(offline_devices)} device(s) are OFFLINE:")
            for device in offline_devices:
                print(f"   🔴 {device['name']} at {device['ip_address']}")
                if 'error' in device:
                    print(f"      Error: {device['error']}")
        else:
            print(f"\n✅ All {len(status['devices'])} devices are currently ONLINE")
    
    # Test 4: Show what web UI indicators should look like
    print("\n📋 Test 3: Web UI Offline Indicators")
    print("-" * 40)
    print("🌐 In the web browser at http://localhost:5000:")
    print("   📊 Status monitoring section should show:")
    if status:
        summary = status['summary']
        if summary['offline'] == 0:
            print("      🟢 'All devices online (N)'")
        elif summary['online'] == 0:
            print("      🔴 'All devices offline (N)'")
        else:
            print(f"      🟡 '{summary['online']}/{summary['total']} devices online'")
        
        print("   🎨 Offline device cards should have:")
        print("      • Red left border")
        print("      • 70% opacity (dimmed appearance)")
        print("      • 'OFF (OFFLINE)' status badge")
        print("      • Pulsing offline animation")

def monitor_offline_detection():
    """Continuously monitor for devices going offline"""
    print("\n🔍 Starting Offline Detection Monitor")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    
    previous_status = None
    
    try:
        while True:
            current_status = get_device_status()
            
            if current_status and previous_status:
                # Check for status changes
                prev_devices = {d['udn']: d for d in previous_status['devices']}
                curr_devices = {d['udn']: d for d in current_status['devices']}
                
                for udn, curr_device in curr_devices.items():
                    if udn in prev_devices:
                        prev_device = prev_devices[udn]
                        
                        # Check for connection status changes
                        if prev_device['connection_status'] != curr_device['connection_status']:
                            timestamp = datetime.now().strftime('%H:%M:%S')
                            if curr_device['connection_status'] == 'offline':
                                print(f"🔴 [{timestamp}] DEVICE WENT OFFLINE: {curr_device['name']} ({curr_device['ip_address']})")
                                if 'error' in curr_device:
                                    print(f"    Error: {curr_device['error']}")
                            elif curr_device['connection_status'] == 'online':
                                print(f"🟢 [{timestamp}] DEVICE CAME ONLINE: {curr_device['name']} ({curr_device['ip_address']})")
            
            if current_status:
                summary = current_status['summary']
                if summary['offline'] > 0:
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    print(f"⚠️  [{timestamp}] {summary['offline']}/{summary['total']} devices offline")
            
            previous_status = current_status
            time.sleep(15)  # Check every 15 seconds
            
    except KeyboardInterrupt:
        print("\n\n🛑 Offline detection monitoring stopped")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "monitor":
        monitor_offline_detection()
    else:
        test_offline_scenarios()
        
        print("\n" + "=" * 60)
        print("💡 Usage:")
        print("   python3 test_offline_detection.py         # Run tests once")
        print("   python3 test_offline_detection.py monitor # Monitor continuously")
        print("\n🔧 To trigger offline detection:")
        print("   • Unplug device from power")
        print("   • Block device network access")
        print("   • Move device out of WiFi range")
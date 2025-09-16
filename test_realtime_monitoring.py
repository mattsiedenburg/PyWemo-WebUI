#!/usr/bin/env python3
"""
Real-time Status Monitoring Test Script

This script tests the actual API status monitoring functionality that the 
web UI uses. It will continuously poll the /devices/status endpoint and
detect changes in device states, allowing you to verify manual button 
press detection.
"""

import requests
import time
import json
from datetime import datetime

API_BASE = "http://localhost:5000"
POLL_INTERVAL = 15  # seconds

def get_device_status():
    """Get current device status from the API"""
    try:
        response = requests.get(f"{API_BASE}/devices/status", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error getting device status: {e}")
        return None

def format_device_state(device):
    """Format device info for display"""
    state_emoji = "🟢" if device["state"] == "on" else "🔴" if device["state"] == "off" else "🟡"
    connection_emoji = "📶" if device["connection_status"] == "online" else "📵"
    return f"{state_emoji}{connection_emoji} {device['name']} ({device['ip_address']}) - {device['state'].upper()}"

def print_status_summary(status_data):
    """Print a formatted status summary"""
    timestamp = datetime.fromtimestamp(status_data['timestamp']).strftime('%H:%M:%S')
    summary = status_data['summary']
    
    print(f"\n📊 Status Summary [{timestamp}]:")
    print(f"   Total devices: {summary['total']}")
    print(f"   Online: {summary['online']} | Offline: {summary['offline']} | Unknown: {summary['unknown']}")
    
    for device in status_data['devices']:
        print(f"   {format_device_state(device)}")

def detect_changes(previous_status, current_status):
    """Detect and report changes between two status snapshots"""
    if not previous_status or not current_status:
        return []
    
    changes = []
    
    # Create lookup dictionaries
    prev_devices = {d['udn']: d for d in previous_status['devices']}
    curr_devices = {d['udn']: d for d in current_status['devices']}
    
    for udn, curr_device in curr_devices.items():
        if udn in prev_devices:
            prev_device = prev_devices[udn]
            
            # Check for state changes
            if prev_device['state'] != curr_device['state']:
                changes.append({
                    'type': 'state_change',
                    'device': curr_device['name'],
                    'udn': udn,
                    'ip': curr_device['ip_address'],
                    'old_state': prev_device['state'],
                    'new_state': curr_device['state']
                })
            
            # Check for connection status changes
            if prev_device['connection_status'] != curr_device['connection_status']:
                changes.append({
                    'type': 'connection_change',
                    'device': curr_device['name'],
                    'udn': udn,
                    'ip': curr_device['ip_address'],
                    'old_status': prev_device['connection_status'],
                    'new_status': curr_device['connection_status']
                })
    
    return changes

def print_changes(changes):
    """Print detected changes with appropriate formatting"""
    if not changes:
        return
    
    print(f"\n🔔 DETECTED CHANGES:")
    for change in changes:
        if change['type'] == 'state_change':
            old_emoji = "🟢" if change['old_state'] == "on" else "🔴"
            new_emoji = "🟢" if change['new_state'] == "on" else "🔴"
            print(f"   🔄 {change['device']} ({change['ip']}) STATE: {old_emoji}{change['old_state'].upper()} → {new_emoji}{change['new_state'].upper()}")
        elif change['type'] == 'connection_change':
            print(f"   📶 {change['device']} ({change['ip']}) CONNECTION: {change['old_status'].upper()} → {change['new_status'].upper()}")

def main():
    print("🚀 Starting Real-time Status Monitoring Test")
    print(f"📡 Polling {API_BASE}/devices/status every {POLL_INTERVAL} seconds")
    print("🔴 Press physical buttons on your WeMo devices to test manual change detection")
    print("🛑 Press Ctrl+C to stop monitoring\n")
    
    previous_status = None
    poll_count = 0
    
    try:
        while True:
            poll_count += 1
            print(f"📊 Poll #{poll_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            current_status = get_device_status()
            if current_status:
                # Detect changes from previous poll
                changes = detect_changes(previous_status, current_status)
                
                if changes:
                    print_changes(changes)
                    print_status_summary(current_status)
                else:
                    print("   ✅ No changes detected")
                
                previous_status = current_status
            else:
                print("   ❌ Failed to get status")
            
            print("-" * 80)
            
            # Wait for next poll
            time.sleep(POLL_INTERVAL)
            
    except KeyboardInterrupt:
        print(f"\n\n🛑 Monitoring stopped after {poll_count} polls")
        if previous_status:
            print("\n📄 Final Status:")
            print_status_summary(previous_status)

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Test script to verify manual device state change detection.

This script demonstrates how manual button presses on WeMo devices
can be detected by polling the device state directly.
"""

import requests
import time
import json
from datetime import datetime

def get_device_states():
    """Get current states of all devices."""
    try:
        response = requests.get('http://localhost:5000/devices', timeout=5)
        if response.status_code == 200:
            devices = response.json()
            states = {}
            
            for device in devices:
                udn = device['udn']
                name = device['name']
                
                # Get current device state
                try:
                    state_response = requests.post(
                        f'http://localhost:5000/device/{udn}/get_state',
                        json={"args": [], "kwargs": {}},
                        timeout=5
                    )
                    if state_response.status_code == 200:
                        result = state_response.json()
                        state = result.get('result', 'unknown')
                        states[udn] = {
                            'name': name,
                            'state': 'ON' if state == 1 else 'OFF' if state == 0 else 'UNKNOWN',
                            'numeric_state': state
                        }
                    else:
                        states[udn] = {
                            'name': name,
                            'state': 'ERROR',
                            'numeric_state': None
                        }
                except Exception as e:
                    states[udn] = {
                        'name': name, 
                        'state': 'OFFLINE',
                        'numeric_state': None,
                        'error': str(e)
                    }
            
            return states
        else:
            print(f"Error getting devices: {response.status_code}")
            return {}
    except Exception as e:
        print(f"Error connecting to API: {e}")
        return {}

def monitor_device_changes(polling_interval=10):
    """Monitor devices for state changes."""
    print("🔄 Starting manual device change detection test...")
    print(f"📊 Polling every {polling_interval} seconds")
    print("👆 Press physical buttons on your WeMo devices to test detection")
    print("-" * 60)
    
    previous_states = {}
    
    while True:
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            current_states = get_device_states()
            
            if not current_states:
                print(f"[{timestamp}] ❌ No devices found or API not ready")
                time.sleep(polling_interval)
                continue
            
            # Check for changes
            changes_detected = False
            
            for udn, state_info in current_states.items():
                device_name = state_info['name']
                current_state = state_info['state']
                
                if udn in previous_states:
                    previous_state = previous_states[udn]['state']
                    
                    if current_state != previous_state:
                        changes_detected = True
                        print(f"[{timestamp}] 🔄 CHANGE DETECTED: {device_name}")
                        print(f"             └── {previous_state} → {current_state}")
                else:
                    # First time seeing this device
                    print(f"[{timestamp}] 📱 Monitoring: {device_name} ({current_state})")
            
            if not changes_detected and previous_states:
                # No changes, just show current status
                device_count = len(current_states)
                on_count = sum(1 for s in current_states.values() if s['state'] == 'ON')
                off_count = sum(1 for s in current_states.values() if s['state'] == 'OFF')
                print(f"[{timestamp}] ✅ Monitoring {device_count} devices: {on_count} ON, {off_count} OFF")
            
            previous_states = current_states.copy()
            time.sleep(polling_interval)
            
        except KeyboardInterrupt:
            print("\n\n🛑 Monitoring stopped by user")
            break
        except Exception as e:
            print(f"[{timestamp}] ❌ Error during monitoring: {e}")
            time.sleep(polling_interval)

if __name__ == "__main__":
    print("🎯 Manual Device Change Detection Test")
    print("=" * 50)
    
    # Wait for API to be ready
    print("⏳ Waiting for PyWemo API to be ready...")
    api_ready = False
    max_wait = 180  # 3 minutes max wait
    wait_time = 0
    
    while not api_ready and wait_time < max_wait:
        try:
            response = requests.get('http://localhost:5000/devices', timeout=5)
            if response.status_code == 200:
                devices = response.json()
                if devices:
                    print(f"✅ API ready! Found {len(devices)} devices")
                    api_ready = True
                else:
                    print("⏳ API ready but no devices found yet...")
                    time.sleep(10)
                    wait_time += 10
            else:
                print(f"⏳ API not ready (status {response.status_code})...")
                time.sleep(10)
                wait_time += 10
        except Exception as e:
            print(f"⏳ Waiting for API... ({e})")
            time.sleep(10)
            wait_time += 10
    
    if api_ready:
        print("\n🚀 Starting monitoring...")
        print("💡 Instructions:")
        print("   1. Leave this script running")
        print("   2. Walk to your WeMo devices")
        print("   3. Press the physical buttons")
        print("   4. Watch for changes to be detected here!")
        print()
        
        monitor_device_changes(polling_interval=15)  # Check every 15 seconds
    else:
        print("❌ API not ready after 3 minutes. Please check if the container is running.")
        print("   Try: docker logs pywemo-status")
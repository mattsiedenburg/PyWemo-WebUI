#!/usr/bin/env python3
"""
Enhanced State Interface Demo
Demonstrates the new visual state indicators and enhanced feedback
"""

import requests
import time
import json
import sys

BASE_URL = "http://localhost:5000"

def make_request(method, endpoint, data=None):
    """Make HTTP request with error handling"""
    try:
        if method == "GET":
            response = requests.get(f"{BASE_URL}{endpoint}")
        elif method == "POST":
            response = requests.post(f"{BASE_URL}{endpoint}", json=data)
        
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None

def print_header(title):
    """Print formatted header"""
    print("\n" + "="*60)
    print(f"🎯 {title}")
    print("="*60)

def print_device_state(state):
    """Print device state with emoji"""
    if state == 1:
        print("🟢 Device State: ON")
    elif state == 0:
        print("🔴 Device State: OFF") 
    else:
        print("🟡 Device State: UNKNOWN")

def main():
    print("🚀 PyWemo API Enhanced State Interface Demo")
    print("=" * 60)
    
    # Check if API is accessible
    print("🔗 Checking API connectivity...")
    result = make_request("GET", "/devices")
    if result is None:
        print("❌ Cannot connect to PyWemo API at http://localhost:5000")
        print("   Make sure the container is running with: docker-compose up -d")
        sys.exit(1)
    
    print("✅ API is accessible!")
    
    # Discover devices
    print_header("Device Discovery")
    
    print("📡 Discovering devices...")
    devices = make_request("GET", "/devices")
    
    if not devices or len(devices) == 0:
        print("📱 No devices found. Adding test devices...")
        
        # Add known devices
        test_devices = ["192.168.16.153", "192.168.16.225"]
        for ip in test_devices:
            print(f"   Adding device at {ip}...")
            result = make_request("POST", "/device/discover_by_ip", {"ip": ip})
            if result:
                print(f"   ✅ Added: {result.get('name', 'Unknown')} ({result.get('model', 'Unknown')})")
        
        # Refresh device list
        devices = make_request("GET", "/devices")
    
    if not devices:
        print("❌ No devices available for demo")
        sys.exit(1)
    
    print(f"✅ Found {len(devices)} device(s):")
    for i, device in enumerate(devices, 1):
        print(f"   {i}. {device['name']} ({device['model']})")
        print(f"      UDN: {device['udn']}")
    
    # Demo enhanced state interface
    if devices:
        device = devices[0]  # Use first device
        udn = device['udn']
        name = device['name']
        
        print_header(f"Enhanced State Interface Demo - {name}")
        
        print("🎬 Demonstrating enhanced state visualization and feedback...")
        
        # 1. Get current state
        print("\n1️⃣ Getting current device state...")
        result = make_request("GET", f"/device/{udn}/get_state")
        if result:
            initial_state = result.get('result')
            print_device_state(initial_state)
            print(f"   Raw API response: {json.dumps(result, indent=2)}")
        
        # 2. Toggle device state
        print("\n2️⃣ Toggling device state...")
        print("🔄 Executing toggle command...")
        result = make_request("POST", f"/device/{udn}/toggle")
        if result:
            print("✅ Toggle command sent successfully")
            print(f"   API response: {json.dumps(result, indent=2)}")
        
        # Wait for device to respond
        print("⏳ Waiting for device to update...")
        time.sleep(2)
        
        # 3. Verify new state
        print("\n3️⃣ Verifying new state...")
        result = make_request("GET", f"/device/{udn}/get_state")
        if result:
            new_state = result.get('result')
            print_device_state(new_state)
            
            if initial_state is not None and new_state != initial_state:
                print("🎉 State change confirmed!")
                print(f"   Changed from: {initial_state} → {new_state}")
            else:
                print("⚠️  State may not have changed or device didn't respond")
        
        # 4. Demonstrate explicit ON/OFF commands
        print("\n4️⃣ Testing explicit ON/OFF commands...")
        
        # Turn OFF
        print("🔴 Turning device OFF...")
        result = make_request("POST", f"/device/{udn}/off")
        if result:
            time.sleep(1)
            result = make_request("GET", f"/device/{udn}/get_state")
            if result:
                print_device_state(result.get('result'))
        
        # Turn ON
        print("🟢 Turning device ON...")
        result = make_request("POST", f"/device/{udn}/on")
        if result:
            time.sleep(1)
            result = make_request("GET", f"/device/{udn}/get_state")
            if result:
                print_device_state(result.get('result'))
    
    # Show web interface info
    print_header("Web Interface Features")
    
    print("🌐 Enhanced Web Interface is available at:")
    print("   📍 http://localhost:5000")
    print()
    print("✨ New Features:")
    print("   • 🎨 Visual state indicators (ON/OFF/UNKNOWN)")
    print("   • 🔄 Real-time state updates")
    print("   • 🎯 Enhanced feedback messages") 
    print("   • 💫 Animated state indicators")
    print("   • 🔄 Auto-refresh after state changes")
    print("   • 🟢🔴🟡 Color-coded status badges")
    print()
    print("🎮 Device Controls:")
    print("   • 📊 Get State - Shows current ON/OFF status")
    print("   • 🔧 Control Device - Access all device methods")
    print("   • 🔄 Toggle - Quick ON/OFF toggle")
    print()
    print("💡 The interface will now show:")
    print("   • Real-time state badges on each device")
    print("   • Automatic state refresh after commands")
    print("   • Enhanced status messages with emojis")
    print("   • Smooth animations and transitions")
    
    print_header("Demo Complete!")
    print("🎉 Enhanced State Interface is ready!")
    print("🌐 Visit http://localhost:5000 to see the improvements in action!")
    print("✨ Device state indicators will show ON/OFF status in real-time")

if __name__ == "__main__":
    main()
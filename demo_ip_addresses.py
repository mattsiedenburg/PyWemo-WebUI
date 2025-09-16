#!/usr/bin/env python3
"""
IP Address Integration Demo
Demonstrates the new IP address display feature in the web interface
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
    print(f"🌐 {title}")
    print("="*60)

def display_device_info(device):
    """Display enhanced device information with IP address"""
    print(f"📱 {device['name']} ({device['model']})")
    print(f"   🌐 IP Address: {device['ip_address']}")
    print(f"   🔢 Serial: {device['serial'] or 'N/A'}")
    print(f"   🔗 UDN: {device['udn']}")
    print()

def main():
    print("🚀 PyWemo API - IP Address Integration Demo")
    print("=" * 60)
    
    # Check API connectivity
    print("🔗 Checking API connectivity...")
    result = make_request("GET", "/devices")
    if result is None:
        print("❌ Cannot connect to PyWemo API at http://localhost:5000")
        print("   Make sure the container is running with: docker-compose up -d")
        sys.exit(1)
    
    print("✅ API is accessible!")
    
    print_header("Device Discovery with IP Address Tracking")
    
    # Check existing devices
    print("📡 Checking existing devices...")
    devices = make_request("GET", "/devices")
    
    if not devices or len(devices) == 0:
        print("📱 No devices found. Adding test devices...")
        
        # Add known devices
        test_devices = [
            {"ip": "192.168.16.153", "expected_name": "Wemo Mini #1"},
            {"ip": "192.168.16.225", "expected_name": "Wemo Mini #2"}
        ]
        
        for device_info in test_devices:
            print(f"   Adding device at {device_info['ip']}...")
            result = make_request("POST", "/device/discover_by_ip", {"ip": device_info['ip']})
            
            if result:
                print(f"   ✅ Discovered: {result.get('name', 'Unknown')}")
                print(f"      🌐 IP Address: {result.get('ip_address', 'Unknown')}")
                print(f"      📋 Model: {result.get('model', 'Unknown')}")
                if result.get('already_discovered'):
                    print(f"      ℹ️  Device was already known")
                else:
                    print(f"      🆕 New device added")
                print()
        
        # Refresh device list
        devices = make_request("GET", "/devices")
    
    # Display all devices with IP addresses
    print_header("Discovered Devices with IP Addresses")
    
    if devices and len(devices) > 0:
        print(f"✅ Found {len(devices)} device(s) with IP address information:")
        print()
        
        for i, device in enumerate(devices, 1):
            print(f"{i}. ", end="")
            display_device_info(device)
    else:
        print("❌ No devices available")
        sys.exit(1)
    
    # Test device control with IP context
    print_header("Device Control with IP Address Context")
    
    if devices:
        device = devices[0]
        print(f"🎯 Testing device control for {device['name']} at {device['ip_address']}:")
        print()
        
        # Get current state
        print("1️⃣ Getting device state...")
        result = make_request("GET", f"/device/{device['udn']}/get_state")
        if result:
            state = result.get('result')
            state_text = "ON" if state == 1 else "OFF" if state == 0 else "UNKNOWN"
            state_emoji = "🟢" if state == 1 else "🔴" if state == 0 else "🟡"
            print(f"   {state_emoji} Device at {device['ip_address']} is currently {state_text}")
        
        # Test connectivity by IP
        print(f"\n2️⃣ Testing direct IP connectivity...")
        try:
            # Try accessing device directly via IP
            direct_response = requests.get(f"http://{device['ip_address']}:49153/setup.xml", timeout=5)
            if direct_response.status_code == 200:
                print(f"   ✅ Device at {device['ip_address']} is directly accessible")
                print(f"   📊 Response size: {len(direct_response.content)} bytes")
            else:
                print(f"   ⚠️  Device responded with status: {direct_response.status_code}")
        except Exception as e:
            print(f"   ❌ Direct access failed: {e}")
    
    # Show web interface improvements
    print_header("Enhanced Web Interface Features")
    
    print("🌐 Enhanced Web Interface now includes IP addresses!")
    print("📍 Available at: http://localhost:5000")
    print()
    print("✨ New IP Address Features:")
    print("   • 🌐 IP address displayed prominently on each device card")
    print("   • 💻 Monospace font styling for better readability")
    print("   • 🎨 Subtle background highlighting for IP addresses")
    print("   • 📋 Copy-friendly format for network troubleshooting")
    print()
    print("📱 Device Card Layout:")
    print("   • Device name and model at the top")
    print("   • Real-time state indicator (ON/OFF/UNKNOWN)")
    print("   • 🆕 IP Address prominently displayed")
    print("   • Serial number and UDN for technical reference")
    print("   • Control buttons (Get State, Toggle, Control Device)")
    print()
    print("🎯 Benefits of IP Address Display:")
    print("   • 📍 Easy device identification on your network")
    print("   • 🔧 Simplified troubleshooting and network analysis")
    print("   • 🔗 Direct device access for advanced users")
    print("   • 📊 Network topology understanding")
    print("   • ⚡ Quick device location for physical access")
    
    # API Documentation
    print_header("Updated API Documentation")
    
    print("📚 API responses now include 'ip_address' field:")
    print()
    print("📡 GET /devices:")
    if devices:
        example_device = devices[0]
        print("```json")
        print(json.dumps({
            "name": example_device["name"],
            "model": example_device["model"],
            "udn": example_device["udn"],
            "serial": example_device["serial"],
            "ip_address": example_device["ip_address"]  # New field!
        }, indent=2))
        print("```")
    
    print("\n🔍 POST /device/discover_by_ip:")
    print("```json")
    print(json.dumps({
        "name": "Wemo Mini",
        "model": "Socket", 
        "udn": "uuid:Socket-1_0-...",
        "serial": None,
        "ip_address": "192.168.16.153",  # New field!
        "already_discovered": False,
        "message": "Device discovered and added successfully"
    }, indent=2))
    print("```")
    
    print_header("Demo Complete!")
    print("🎉 IP Address integration is fully operational!")
    print("🌐 Visit http://localhost:5000 to see IP addresses in the web interface!")
    print("✨ Device management is now easier with visible IP addresses!")

if __name__ == "__main__":
    main()
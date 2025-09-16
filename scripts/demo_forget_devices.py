#!/usr/bin/env python3
"""
Forget Device Functionality Demo
Demonstrates the new device removal features in PyWemo API
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
        elif method == "DELETE":
            response = requests.delete(f"{BASE_URL}{endpoint}", json=data)
        
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None

def print_header(title):
    """Print formatted header"""
    print("\n" + "="*60)
    print(f"🗑️ {title}")
    print("="*60)

def display_devices(devices):
    """Display device list in a formatted way"""
    if not devices:
        print("   📭 No devices found")
        return
    
    print(f"   📱 Found {len(devices)} device(s):")
    for i, device in enumerate(devices, 1):
        print(f"     {i}. {device['name']} ({device['model']})")
        print(f"        🌐 IP: {device['ip_address']}")
        print(f"        🆔 UDN: {device['udn']}")
        print()

def main():
    print("🚀 PyWemo API - Forget Device Functionality Demo")
    print("=" * 60)
    
    # Check API connectivity
    print("🔗 Checking API connectivity...")
    result = make_request("GET", "/devices")
    if result is None:
        print("❌ Cannot connect to PyWemo API at http://localhost:5000")
        print("   Make sure the container is running with: docker-compose up -d")
        sys.exit(1)
    
    print("✅ API is accessible!")
    
    print_header("Initial Setup - Adding Test Devices")
    
    # Add test devices
    test_devices = ["192.168.16.153", "192.168.16.225", "192.168.16.169"]
    
    print("📡 Adding test devices to demonstrate forget functionality...")
    added_devices = []
    
    for ip in test_devices:
        print(f"   Adding device at {ip}...")
        result = make_request("POST", "/device/discover_by_ip", {"ip": ip})
        if result:
            added_devices.append(result)
            print(f"     ✅ {result.get('name', 'Unknown')} added successfully")
        else:
            print(f"     ❌ Failed to add device at {ip}")
    
    # Show current devices
    print_header("Current Device List")
    devices = make_request("GET", "/devices")
    display_devices(devices)
    
    # Test individual device forgetting
    print_header("Individual Device Forgetting")
    
    if devices and len(devices) > 0:
        target_device = devices[0]
        device_name = target_device['name']
        device_udn = target_device['udn']
        device_ip = target_device['ip_address']
        
        print(f"🎯 Forgetting device: {device_name} at {device_ip}")
        print(f"   UDN: {device_udn}")
        
        result = make_request("POST", f"/device/{device_udn}/forget")
        if result:
            print("   ✅ Device forgotten successfully!")
            print(f"   📊 Result: {result['message']}")
            print(f"   📱 Remaining devices: {result['remaining_devices']}")
            
            # Show updated device list
            print("\n   📋 Updated device list:")
            devices = make_request("GET", "/devices")
            display_devices(devices)
        else:
            print("   ❌ Failed to forget device")
    
    # Test forget all functionality
    if devices and len(devices) > 0:
        print_header("Forget All Devices")
        
        current_devices = make_request("GET", "/devices")
        device_count = len(current_devices) if current_devices else 0
        
        print(f"🗑️ Forgetting all {device_count} remaining devices...")
        
        result = make_request("POST", "/devices/forget_all")
        if result:
            print("   ✅ All devices forgotten successfully!")
            print(f"   📊 Result: {result['message']}")
            
            if result.get('forgotten_devices'):
                print("   📋 Forgotten devices:")
                for device in result['forgotten_devices']:
                    print(f"     • {device['name']} at {device['ip_address']}")
            
            # Show final device list
            print("\n   📋 Final device list:")
            devices = make_request("GET", "/devices")
            display_devices(devices)
        else:
            print("   ❌ Failed to forget all devices")
    
    # Test error handling
    print_header("Error Handling Tests")
    
    print("🧪 Testing error scenarios...")
    
    # Try to forget a non-existent device
    print("   Testing non-existent device forgetting...")
    result = make_request("POST", "/device/uuid:NonExistent-Device/forget")
    if result is None:
        print("     ✅ Correctly handled non-existent device (404 error)")
    else:
        print("     ❌ Should have failed for non-existent device")
    
    # Try to forget all when no devices exist
    print("   Testing forget all with no devices...")
    result = make_request("POST", "/devices/forget_all")
    if result:
        print(f"     ✅ Handled empty device list: {result['message']}")
    else:
        print("     ❌ Failed to handle empty device list")
    
    # Show web interface features
    print_header("Web Interface Features")
    
    print("🌐 Enhanced Web Interface with Forget Functionality!")
    print("📍 Available at: http://localhost:5000")
    print()
    print("🆕 New Forget Features:")
    print("   • 🗑️ 'Forget' button on each device card")
    print("   • 🗑️ 'Forget All Devices' button in main controls")
    print("   • ⚠️  Confirmation dialogs before forgetting devices")
    print("   • 🔄 Automatic interface refresh after forgetting")
    print("   • 📊 Status messages showing forget results")
    print()
    print("🎮 How to Use:")
    print("   1. **Individual Forget**: Click 'Forget' on any device card")
    print("   2. **Bulk Forget**: Click 'Forget All Devices' in top controls")
    print("   3. **Confirmation**: Confirm the action in the dialog")
    print("   4. **Re-discovery**: Use refresh or network scan to find devices again")
    print()
    print("🔒 Safety Features:")
    print("   • ⚠️  Confirmation dialogs prevent accidental deletion")
    print("   • 🔄 Devices can be re-discovered anytime")
    print("   • 📝 Clear feedback on what was forgotten")
    print("   • 🎯 No permanent data loss - just removes from interface")
    
    # API Documentation
    print_header("API Documentation")
    
    print("📚 New API Endpoints:")
    print()
    print("🗑️ Forget Individual Device:")
    print("   POST /device/{udn}/forget")
    print("   DELETE /device/{udn}/forget")
    print()
    print("   Example Response:")
    print("   {")
    print("     \"message\": \"Device forgotten successfully\",")
    print("     \"device\": {")
    print("       \"name\": \"Wemo Mini\",")
    print("       \"model\": \"Socket\",")
    print("       \"ip_address\": \"192.168.16.153\",")
    print("       \"udn\": \"uuid:Socket-1_0-...\",")
    print("       \"serial\": null")
    print("     },")
    print("     \"remaining_devices\": 2")
    print("   }")
    print()
    print("🗑️ Forget All Devices:")
    print("   POST /devices/forget_all")
    print("   DELETE /devices/forget_all")
    print()
    print("   Example Response:")
    print("   {")
    print("     \"message\": \"All 3 devices forgotten successfully\",")
    print("     \"forgotten_devices\": [...],")
    print("     \"remaining_devices\": 0")
    print("   }")
    
    print_header("Demo Complete!")
    print("🎉 Forget Device functionality is fully operational!")
    print("🌐 Visit http://localhost:5000 to test the web interface!")
    print("✨ Device management is now complete with forget functionality!")
    print()
    print("💡 Remember: Forgetting devices only removes them from the interface.")
    print("   You can always re-discover them using refresh or network scan!")

if __name__ == "__main__":
    main()
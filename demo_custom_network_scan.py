#!/usr/bin/env python3
"""
🌐 Custom Network Scanning Demo Script
======================================

This script demonstrates the new configurable network scanning feature
that allows users to specify custom network ranges in CIDR notation.

Features demonstrated:
- Network range validation (CIDR, subnet mask, single IP)
- Custom network scanning with different ranges
- Error handling and validation feedback
- Network information display

Author: PyWemo API Enhanced
Date: 2025-09-14
"""

import requests
import json
import time
from datetime import datetime

# Configuration
API_BASE = "http://localhost:5000"

def print_header(title, icon="🌐"):
    """Print a formatted header."""
    print(f"\n{icon} {title}")
    print("=" * (len(title) + 3))

def print_step(step_num, description, icon="✨"):
    """Print a formatted step."""
    print(f"\n{icon} Step {step_num}: {description}")

def validate_network_range(network_input):
    """Validate a network range using the API."""
    try:
        response = requests.post(
            f"{API_BASE}/devices/network/validate",
            headers={"Content-Type": "application/json"},
            json={"network": network_input}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data["valid"]:
                info = data["info"]
                print(f"✅ Valid network range: {network_input}")
                print(f"   Normalized: {data['normalized']}")
                print(f"   Network: {info['network_address']}")
                print(f"   Hosts to scan: {info['host_count']}")
                if info['host_count'] > 1:
                    print(f"   IP range: {info['first_host']} - {info['last_host']}")
                print(f"   Estimated scan time: {info['estimated_scan_time']}")
                if info['host_count'] > 100:
                    print(f"   ⚠️  Large network - scan may take a while")
                return True, data['normalized']
            else:
                print(f"❌ Invalid network range: {network_input}")
                print(f"   Error: {data['error']}")
                return False, None
        else:
            error_data = response.json()
            print(f"❌ Validation failed: {error_data.get('error', 'Unknown error')}")
            return False, None
            
    except Exception as e:
        print(f"❌ Error validating network: {e}")
        return False, None

def scan_custom_network(network_range, timeout=15):
    """Perform a custom network scan."""
    try:
        print(f"🚀 Starting network scan for: {network_range}")
        start_time = time.time()
        
        response = requests.post(
            f"{API_BASE}/devices/discovery/network-scan",
            headers={"Content-Type": "application/json"},
            json={
                "custom_network": network_range,
                "timeout": timeout
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            scan_time = time.time() - start_time
            
            print(f"🎉 Scan completed in {scan_time:.1f}s")
            print(f"   Status: {data['status']}")
            print(f"   Devices found: {data['devices_found']}")
            print(f"   Network scanned: {data['custom_network']}")
            print(f"   Scan timeout: {data['scan_timeout']}s")
            
            return data['devices_found']
        else:
            error_data = response.json()
            print(f"❌ Scan failed: {error_data.get('error', 'Unknown error')}")
            return 0
            
    except Exception as e:
        print(f"❌ Error during scan: {e}")
        return 0

def get_discovered_devices():
    """Get the list of currently discovered devices."""
    try:
        response = requests.get(f"{API_BASE}/devices")
        if response.status_code == 200:
            devices = response.json()
            print(f"📱 Currently discovered devices: {len(devices)}")
            for i, device in enumerate(devices, 1):
                print(f"   {i}. {device['name']} ({device['model']}) - IP: {device['ip_address']}")
            return len(devices)
        else:
            print("❌ Error getting device list")
            return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return 0

def clear_all_devices():
    """Clear all discovered devices."""
    try:
        response = requests.post(f"{API_BASE}/devices/forget_all")
        if response.status_code == 200:
            data = response.json()
            print(f"🗑️ Cleared {len(data['forgotten_devices'])} devices")
            return True
        else:
            print("❌ Error clearing devices")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Main demo function."""
    print_header("Custom Network Scanning Demo", "🌐")
    print("This demo showcases the new configurable network scanning feature.")
    print("You can now specify custom network ranges in CIDR notation!")
    
    # Test network range validation
    print_header("Network Range Validation", "🔍")
    
    test_networks = [
        "192.168.1.0/24",           # Standard CIDR notation
        "192.168.1.0/255.255.255.0", # Subnet mask format
        "192.168.16.169",           # Single IP address
        "10.0.0.0/16",              # Larger network
        "invalid.network",          # Invalid format
        "192.168.1.0/33",           # Invalid CIDR
        "192.168.1.256/24",         # Invalid IP
    ]
    
    valid_networks = []
    
    for i, network in enumerate(test_networks, 1):
        print_step(i, f"Validating: {network}")
        is_valid, normalized = validate_network_range(network)
        if is_valid:
            valid_networks.append(normalized)
    
    # Demo custom network scanning
    print_header("Custom Network Scanning", "🚀")
    
    print("🧹 Clearing existing devices for clean demo...")
    clear_all_devices()
    
    if valid_networks:
        print(f"\n✅ Found {len(valid_networks)} valid networks to scan")
        
        # Scan a single IP first (fast)
        single_ip_networks = [n for n in valid_networks if "/32" in n]
        if single_ip_networks:
            print_step(1, f"Scanning single IP: {single_ip_networks[0]}")
            found = scan_custom_network(single_ip_networks[0], timeout=10)
            get_discovered_devices()
        
        # Scan a small network range
        small_networks = [n for n in valid_networks if "/24" in n]
        if small_networks:
            print_step(2, f"Demo scan of small network: {small_networks[0][:15]}...")
            print("ℹ️  Note: This would scan 254 IPs in a real scenario")
            print("   For demo purposes, we'll use a shorter timeout")
            found = scan_custom_network(small_networks[0], timeout=5)
            get_discovered_devices()
    
    # Show API endpoints summary
    print_header("API Endpoints Summary", "📋")
    print("New endpoints added for configurable network scanning:")
    print()
    print("1. Network Validation:")
    print("   POST /devices/network/validate")
    print("   Body: {\"network\": \"192.168.1.0/24\"}")
    print()
    print("2. Custom Network Scan:")
    print("   POST /devices/discovery/network-scan")
    print("   Body: {\"custom_network\": \"192.168.1.0/24\", \"timeout\": 15}")
    print()
    print("3. Enhanced Refresh:")
    print("   POST /devices/refresh")
    print("   Body: {\"network_scan\": true, \"custom_network\": \"192.168.1.0/24\"}")
    
    # Show supported formats
    print_header("Supported Network Formats", "📝")
    print("✅ CIDR notation: 192.168.1.0/24")
    print("✅ Subnet mask: 192.168.1.0/255.255.255.0")
    print("✅ Single IP: 192.168.1.100 (converted to /32)")
    print("✅ Large networks: 10.0.0.0/8, 172.16.0.0/12")
    print("✅ Small subnets: 192.168.1.0/28 (16 hosts)")
    
    # Web interface info
    print_header("Web Interface", "🌐")
    print("Visit http://localhost:5000 to use the new Custom Network Scan feature:")
    print("• Click '🌐 Custom Network Scan' button")
    print("• Enter network range in any supported format")
    print("• Click '🔍 Validate Network' to verify")
    print("• Adjust timeout if needed")
    print("• Click '🚀 Start Scan' to begin scanning")
    print("• Real-time validation as you type!")
    
    print_header("Demo Complete!", "🎉")
    print("The configurable network scanning feature is now fully operational!")
    print("Users can scan any network range in CIDR notation with validation.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚡ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
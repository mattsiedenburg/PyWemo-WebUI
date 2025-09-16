#!/usr/bin/env python3
"""
Comprehensive test suite for PyWemo API
Tests all endpoints, error handling, and functionality
"""

import requests
import json
import time
import threading
import subprocess
import sys
import os
from concurrent.futures import ThreadPoolExecutor

class PyWemoAPITester:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = []
    
    def log_result(self, test_name, success, message="", response_code=None):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "response_code": response_code
        }
        self.results.append(result)
        print(f"{status}: {test_name}")
        if message:
            print(f"    {message}")
        if response_code:
            print(f"    HTTP {response_code}")
    
    def test_web_interface(self):
        """Test web interface accessibility"""
        try:
            response = self.session.get(self.base_url, timeout=10)
            success = response.status_code == 200 and "WeMo Device Control" in response.text
            self.log_result("Web Interface Access", success, 
                          f"Status: {response.status_code}, Contains title: {'WeMo Device Control' in response.text}",
                          response.status_code)
        except Exception as e:
            self.log_result("Web Interface Access", False, str(e))
    
    def test_static_files(self):
        """Test static file serving"""
        static_files = ["/static/css/style.css", "/static/js/app.js"]
        
        for file_path in static_files:
            try:
                response = self.session.get(f"{self.base_url}{file_path}", timeout=5)
                success = response.status_code == 200
                self.log_result(f"Static File: {file_path}", success, 
                              f"Status: {response.status_code}", response.status_code)
            except Exception as e:
                self.log_result(f"Static File: {file_path}", False, str(e))
    
    def test_device_endpoints(self):
        """Test device-related API endpoints"""
        
        # Test GET /devices
        try:
            response = self.session.get(f"{self.base_url}/devices", timeout=10)
            success = response.status_code == 200
            devices = response.json() if success else []
            self.log_result("GET /devices", success, 
                          f"Found {len(devices)} devices", response.status_code)
        except Exception as e:
            self.log_result("GET /devices", False, str(e))
        
        # Test POST /devices/refresh
        try:
            response = self.session.post(f"{self.base_url}/devices/refresh", 
                                       json={}, timeout=15)
            success = response.status_code == 200
            data = response.json() if success else {}
            self.log_result("POST /devices/refresh", success, 
                          f"Status: {data.get('status', 'unknown')}", response.status_code)
        except Exception as e:
            self.log_result("POST /devices/refresh", False, str(e))
    
    def test_discovery_endpoints(self):
        """Test discovery-related endpoints"""
        
        # Test discovery status
        try:
            response = self.session.get(f"{self.base_url}/devices/discovery/status", timeout=5)
            success = response.status_code == 200
            data = response.json() if success else {}
            self.log_result("GET /devices/discovery/status", success, 
                          f"Auto-discovery: {data.get('auto_discovery_enabled', 'unknown')}", 
                          response.status_code)
        except Exception as e:
            self.log_result("GET /devices/discovery/status", False, str(e))
        
        # Test network scan
        try:
            response = self.session.post(f"{self.base_url}/devices/discovery/network-scan", 
                                       json={"timeout": 5}, timeout=20)
            success = response.status_code == 200
            data = response.json() if success else {}
            self.log_result("POST /devices/discovery/network-scan", success, 
                          f"Devices found: {data.get('devices_found', 'unknown')}", 
                          response.status_code)
        except Exception as e:
            self.log_result("POST /devices/discovery/network-scan", False, str(e))
    
    def test_device_discovery_by_ip(self):
        """Test manual device discovery by IP"""
        
        # Test with invalid IP
        try:
            response = self.session.post(f"{self.base_url}/device/discover_by_ip", 
                                       json={"ip": "192.168.1.999"}, timeout=10)
            success = response.status_code == 400  # Should fail with bad request
            self.log_result("Discover by Invalid IP", success, 
                          "Expected 400 for invalid IP", response.status_code)
        except Exception as e:
            self.log_result("Discover by Invalid IP", False, str(e))
        
        # Test with likely non-WeMo IP
        try:
            response = self.session.post(f"{self.base_url}/device/discover_by_ip", 
                                       json={"ip": "8.8.8.8"}, timeout=10)
            success = response.status_code in [400, 404]  # Should fail
            self.log_result("Discover by Non-WeMo IP", success, 
                          "Expected 400/404 for non-WeMo IP", response.status_code)
        except Exception as e:
            self.log_result("Discover by Non-WeMo IP", False, str(e))
    
    def test_error_handling(self):
        """Test error handling"""
        
        # Test non-existent device endpoint
        try:
            response = self.session.get(f"{self.base_url}/device/nonexistent/methods", timeout=5)
            success = response.status_code == 404
            self.log_result("Non-existent Device Methods", success, 
                          "Expected 404 for non-existent device", response.status_code)
        except Exception as e:
            self.log_result("Non-existent Device Methods", False, str(e))
        
        # Test invalid method call
        try:
            response = self.session.post(f"{self.base_url}/device/nonexistent/invalid_method", 
                                       timeout=5)
            success = response.status_code == 404
            self.log_result("Invalid Method Call", success, 
                          "Expected 404 for invalid method", response.status_code)
        except Exception as e:
            self.log_result("Invalid Method Call", False, str(e))
        
        # Test malformed JSON
        try:
            response = self.session.post(f"{self.base_url}/devices/refresh", 
                                       data="invalid json", 
                                       headers={"Content-Type": "application/json"},
                                       timeout=5)
            # Should still work as it falls back to empty dict
            success = response.status_code == 200
            self.log_result("Malformed JSON Handling", success, 
                          "API should handle malformed JSON gracefully", response.status_code)
        except Exception as e:
            self.log_result("Malformed JSON Handling", False, str(e))
    
    def test_debug_endpoint(self):
        """Test debug network detection endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/devices/discovery/debug", timeout=10)
            success = response.status_code == 200
            data = response.json() if success else {}
            local_ip = data.get('local_ip', 'unknown')
            self.log_result("Debug Network Detection", success, 
                          f"Local IP: {local_ip}", response.status_code)
        except Exception as e:
            self.log_result("Debug Network Detection", False, str(e))
    
    def test_concurrent_requests(self):
        """Test concurrent request handling"""
        def make_request():
            try:
                response = self.session.get(f"{self.base_url}/devices", timeout=5)
                return response.status_code == 200
            except:
                return False
        
        try:
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(make_request) for _ in range(10)]
                results = [f.result() for f in futures]
                success_count = sum(results)
                
            success = success_count >= 8  # Allow some failures
            self.log_result("Concurrent Requests", success, 
                          f"{success_count}/10 requests successful")
        except Exception as e:
            self.log_result("Concurrent Requests", False, str(e))
    
    def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting PyWemo API Test Suite")
        print("=" * 50)
        
        test_methods = [
            self.test_web_interface,
            self.test_static_files,
            self.test_device_endpoints,
            self.test_discovery_endpoints,
            self.test_device_discovery_by_ip,
            self.test_error_handling,
            self.test_debug_endpoint,
            self.test_concurrent_requests,
        ]
        
        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                self.log_result(test_method.__name__, False, f"Test method failed: {e}")
            print()  # Add spacing between test groups
        
        # Summary
        print("=" * 50)
        print("📊 Test Summary")
        print("=" * 50)
        
        passed = sum(1 for r in self.results if r["success"])
        total = len(self.results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if total - passed > 0:
            print("\n❌ Failed Tests:")
            for result in self.results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['message']}")
        
        return passed, total

def wait_for_app(url, timeout=30):
    """Wait for the app to be available"""
    print(f"⏳ Waiting for app to be available at {url}...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                print("✅ App is ready!")
                return True
        except:
            pass
        time.sleep(1)
    
    print("❌ App did not become available within timeout")
    return False

if __name__ == "__main__":
    # Check if app is running
    base_url = "http://localhost:5000"
    
    if not wait_for_app(base_url, timeout=15):
        print("❌ Could not connect to PyWemo API. Make sure it's running on localhost:5000")
        sys.exit(1)
    
    # Run tests
    tester = PyWemoAPITester(base_url)
    passed, total = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if passed == total else 1)
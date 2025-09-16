import pywemo
from flask import Flask, request, jsonify, abort, send_from_directory, redirect, url_for
import inspect
import threading
import time
import logging
import ipaddress
import socket
import os
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache

app = Flask(__name__, static_folder='static', static_url_path='/static')

# Enable response compression and caching
@app.after_request
def after_request(response):
    # Cache static files for 1 hour
    if request.endpoint == 'static':
        response.cache_control.max_age = 3600
        response.cache_control.public = True
    
    # Enable compression for appropriate content types
    if response.content_type in ['text/html', 'text/css', 'application/json', 'application/javascript', 'text/javascript']:
        response.headers['Vary'] = 'Accept-Encoding'
    
    return response

# Enhanced discovery system
devices = []
device_map = {}  # Maps device UDN to device instance
discovery_status = {
    "last_discovery": None,
    "discovery_count": 0,
    "auto_discovery_enabled": True,
    "background_discovery_running": False
}

# Scan progress tracking
scan_progress = {
    "is_scanning": False,
    "scan_type": None,  # "network", "refresh", "custom"
    "start_time": None,
    "progress_percent": 0,
    "current_step": "",
    "ips_scanned": 0,
    "total_ips": 0,
    "devices_found": 0,
    "network_range": None,
    "estimated_time_remaining": 0,
    "can_cancel": True
}

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Friendly device names storage
FRIENDLY_NAMES_FILE = '/app/data/friendly_names.json'
friendly_names = {}

def ensure_data_directory():
    """Ensure the data directory exists."""
    os.makedirs(os.path.dirname(FRIENDLY_NAMES_FILE), exist_ok=True)

def load_friendly_names():
    """Load friendly device names from file."""
    global friendly_names
    try:
        if os.path.exists(FRIENDLY_NAMES_FILE):
            with open(FRIENDLY_NAMES_FILE, 'r') as f:
                friendly_names = json.load(f)
        else:
            friendly_names = {}
        logger.info(f"Loaded {len(friendly_names)} friendly device names")
    except Exception as e:
        logger.error(f"Failed to load friendly names: {e}")
        friendly_names = {}

def save_friendly_names():
    """Save friendly device names to file."""
    try:
        ensure_data_directory()
        with open(FRIENDLY_NAMES_FILE, 'w') as f:
            json.dump(friendly_names, f, indent=2)
        logger.debug(f"Saved {len(friendly_names)} friendly device names")
    except Exception as e:
        logger.error(f"Failed to save friendly names: {e}")

def get_device_display_name(device):
    """Get the display name for a device (friendly name if available, otherwise original name)."""
    return friendly_names.get(device.udn, device.name)

def get_device_info_with_friendly_name(device):
    """Get device info including friendly name information."""
    return {
        "name": device.name,
        "friendly_name": friendly_names.get(device.udn),
        "display_name": get_device_display_name(device),
        "udn": device.udn,
        "model": getattr(device, "model_name", None),
        "serial": getattr(device, "serialnumber", None),
        "ip_address": getattr(device, "host", None)
    }

@lru_cache(maxsize=32)
def validate_network_range(network_input):
    """Validate and normalize network range input.
    
    Accepts:
    - CIDR notation: "192.168.1.0/24"
    - IP range with slash: "192.168.1.0/255.255.255.0"
    - Single IP (converted to /32): "192.168.1.100"
    
    Returns:
        tuple: (is_valid, normalized_cidr, error_message)
    """
    if not network_input or not isinstance(network_input, str):
        return False, None, "Network input must be a non-empty string"
    
    network_input = network_input.strip()
    
    try:
        # Try parsing as CIDR notation first
        if '/' in network_input:
            parts = network_input.split('/')
            if len(parts) != 2:
                return False, None, "Invalid network format. Use CIDR notation (e.g., 192.168.1.0/24)"
            
            ip_part, mask_part = parts
            
            # Validate IP address part
            try:
                ipaddress.IPv4Address(ip_part)
            except ValueError:
                return False, None, f"Invalid IP address: {ip_part}"
            
            # Handle subnet mask in different formats
            if mask_part.isdigit():
                # CIDR notation (e.g., /24)
                prefix_len = int(mask_part)
                if not (0 <= prefix_len <= 32):
                    return False, None, "CIDR prefix length must be between 0 and 32"
                cidr = f"{ip_part}/{prefix_len}"
            else:
                # Subnet mask format (e.g., /255.255.255.0)
                try:
                    mask_ip = ipaddress.IPv4Address(mask_part)
                    # Convert subnet mask to prefix length
                    prefix_len = ipaddress.IPv4Network(f"0.0.0.0/{mask_part}", strict=False).prefixlen
                    cidr = f"{ip_part}/{prefix_len}"
                except ValueError:
                    return False, None, f"Invalid subnet mask: {mask_part}"
            
            # Validate the complete network
            network = ipaddress.IPv4Network(cidr, strict=False)
            return True, str(network), None
            
        else:
            # Single IP address - convert to /32
            ip = ipaddress.IPv4Address(network_input)
            return True, f"{ip}/32", None
            
    except ValueError as e:
        return False, None, f"Invalid network format: {str(e)}"
    except Exception as e:
        return False, None, f"Unexpected error validating network: {str(e)}"

def get_network_scan_info(network_range):
    """Get information about a network range for scanning."""
    try:
        network = ipaddress.IPv4Network(network_range, strict=False)
        host_count = len(list(network.hosts()))
        
        return {
            "network_address": str(network.network_address),
            "broadcast_address": str(network.broadcast_address),
            "cidr": str(network),
            "prefix_length": network.prefixlen,
            "host_count": host_count,
            "first_host": str(list(network.hosts())[0]) if host_count > 0 else None,
            "last_host": str(list(network.hosts())[-1]) if host_count > 0 else None,
            "is_single_host": host_count == 1,
            "estimated_scan_time": f"{max(1, host_count * 0.1):.1f}s"
        }
    except Exception as e:
        return {"error": str(e)}

def start_scan_progress(scan_type, network_range=None):
    """Initialize scan progress tracking."""
    global scan_progress
    
    scan_progress.update({
        "is_scanning": True,
        "scan_type": scan_type,
        "start_time": time.time(),
        "progress_percent": 0,
        "current_step": "Starting scan...",
        "ips_scanned": 0,
        "total_ips": 0,
        "devices_found": 0,
        "network_range": network_range,
        "estimated_time_remaining": 0,
        "can_cancel": True
    })

def finish_scan_progress():
    """Mark scan as completed."""
    global scan_progress
    scan_progress["is_scanning"] = False
    scan_progress["can_cancel"] = False

def clear_device_cache(device):
    """Clear all possible PyWemo device caches to force fresh state queries."""
    try:
        # Clear direct device state caches
        if hasattr(device, '_state'):
            device._state = None
            
        if hasattr(device, 'state'):
            try:
                delattr(device, 'state')
            except AttributeError:
                pass
                
        if hasattr(device, '_cached_state'):
            device._cached_state = None
            
        if hasattr(device, 'cache'):
            try:
                if hasattr(device.cache, 'clear'):
                    device.cache.clear()
                elif isinstance(device.cache, dict):
                    device.cache.clear()
            except (AttributeError, TypeError):
                pass
        
        # Clear basicevent caches (common in PyWemo)
        if hasattr(device, 'basicevent'):
            be = device.basicevent
            
            if hasattr(be, '_state'):
                be._state = None
                
            if hasattr(be, 'state'):
                try:
                    delattr(be, 'state')
                except AttributeError:
                    pass
                    
            if hasattr(be, '_cached_state'):
                be._cached_state = None
                
            if hasattr(be, 'cache'):
                try:
                    if hasattr(be.cache, 'clear'):
                        be.cache.clear()
                    elif isinstance(be.cache, dict):
                        be.cache.clear()
                except (AttributeError, TypeError):
                    pass
        
        # Clear any SOAP service caches
        for attr_name in dir(device):
            if not attr_name.startswith('_') and hasattr(device, attr_name):
                attr = getattr(device, attr_name)
                if hasattr(attr, '_cached_state'):
                    attr._cached_state = None
                if hasattr(attr, '_state'):
                    attr._state = None
    except Exception as e:
        logger.debug(f"Error clearing device cache: {e}")

def discover_devices_enhanced(timeout=10, network_scan=False, custom_network=None):
    """Enhanced discovery with multiple methods and timeout handling.
    
    Args:
        timeout: Discovery timeout in seconds
        network_scan: Whether to perform network scanning
        custom_network: Optional custom network range in CIDR notation
    """
    global devices, device_map, discovery_status
    
    logger.info("Starting enhanced device discovery...")
    start_time = time.time()
    
    # Method 1: Standard pywemo discovery
    try:
        logger.info("Method 1: Standard UPnP discovery")
        discovered = pywemo.discover_devices(timeout=timeout)
        for device in discovered:
            if device.udn not in device_map:
                device_map[device.udn] = device
                devices.append(device)
                logger.info(f"Discovered new device: {device.name} ({device.udn})")
    except Exception as e:
        logger.error(f"Standard discovery failed: {e}")
    
    # Method 2: Network scan discovery (if enabled)
    if network_scan:
        try:
            logger.info("Method 2: Network scan discovery")
            
            # Start progress tracking if not already scanning
            if not scan_progress["is_scanning"]:
                start_scan_progress("network", custom_network)
            
            scan_results = scan_network_for_wemo_devices(custom_network=custom_network)
            
            update_scan_progress("Processing discovered devices", 90)
            
            for ip in scan_results:
                try:
                    device = pywemo.discovery.device_from_description(f"http://{ip}:49153/setup.xml")
                    if device and device.udn not in device_map:
                        device_map[device.udn] = device
                        devices.append(device)
                        logger.info(f"Network scan found new device: {device.name} at {ip}")
                except Exception as e:
                    logger.debug(f"Failed to discover device at {ip}: {e}")
                    
        except Exception as e:
            logger.error(f"Network scan discovery failed: {e}")
    
    # Method 3: Known device refresh
    try:
        logger.info("Method 3: Refreshing known devices")
        refresh_known_devices()
    except Exception as e:
        logger.error(f"Known device refresh failed: {e}")
    
    discovery_time = time.time() - start_time
    discovery_status["last_discovery"] = time.time()
    discovery_status["discovery_count"] += 1
    
    # Finish progress tracking if we were scanning
    if scan_progress["is_scanning"]:
        update_scan_progress(f"Discovery completed - Found {len(devices)} devices", 100, scan_progress["total_ips"], len(devices))
        finish_scan_progress()
    
    logger.info(f"Discovery completed in {discovery_time:.2f}s. Found {len(devices)} total devices.")
    return len(devices)

def update_scan_progress(step, progress_percent=None, ips_scanned=None, devices_found=None):
    """Update scan progress status."""
    global scan_progress
    
    scan_progress["current_step"] = step
    if progress_percent is not None:
        scan_progress["progress_percent"] = min(100, max(0, progress_percent))
    if ips_scanned is not None:
        scan_progress["ips_scanned"] = ips_scanned
    if devices_found is not None:
        scan_progress["devices_found"] = devices_found
    
    # Calculate estimated time remaining
    if scan_progress["start_time"] and scan_progress["total_ips"] > 0 and ips_scanned:
        elapsed_time = time.time() - scan_progress["start_time"]
        if ips_scanned > 0:
            avg_time_per_ip = elapsed_time / ips_scanned
            remaining_ips = scan_progress["total_ips"] - ips_scanned
            scan_progress["estimated_time_remaining"] = remaining_ips * avg_time_per_ip

def scan_network_for_wemo_devices(timeout=2, custom_network=None):
    """Scan local network for potential WeMo devices with progress tracking.
    
    Args:
        timeout: Timeout for individual port checks
        custom_network: Optional custom network range in CIDR notation (e.g., "192.168.1.0/24")
    """
    global scan_progress
    found_ips = []
    
    try:
        # Use custom network range if provided, otherwise auto-detect
        if custom_network:
            network_range = custom_network
            logger.info(f"Using custom network range: {network_range}")
        else:
            network_range = get_local_network_range()
            if not network_range:
                logger.error("Could not determine network range for scanning")
                return found_ips
        
        logger.info(f"Scanning network range: {network_range}")
        update_scan_progress(f"Preparing to scan {network_range}", 5)
        
        # Convert to network object and get host count
        network = ipaddress.IPv4Network(network_range, strict=False)
        host_ips = list(network.hosts())
        logger.info(f"Scanning {len(host_ips)} IP addresses...")
        
        scan_progress["total_ips"] = len(host_ips)
        scan_progress["network_range"] = network_range
        update_scan_progress(f"Starting scan of {len(host_ips)} IP addresses", 10)
        
        # Use ThreadPoolExecutor for concurrent scanning
        with ThreadPoolExecutor(max_workers=50) as executor:
            # Create tasks for each IP
            futures = []
            for ip in host_ips:
                future = executor.submit(check_wemo_port, str(ip), timeout)
                futures.append((future, str(ip)))
            
            update_scan_progress("Scanning network for WeMo devices", 15)
            
            # Collect results with progress tracking
            completed = 0
            for future, ip in futures:
                # Check if scan was cancelled
                if not scan_progress["is_scanning"]:
                    logger.info("Network scan cancelled by user")
                    break
                    
                try:
                    if future.result(timeout=timeout + 1):
                        found_ips.append(ip)
                        logger.info(f"✅ Found potential WeMo device at {ip}")
                        scan_progress["devices_found"] = len(found_ips)
                    
                    completed += 1
                    
                    # Update progress
                    progress_percent = 15 + (completed / len(host_ips)) * 75  # 15% to 90%
                    update_scan_progress(
                        f"Scanned {completed}/{len(host_ips)} IPs - Found {len(found_ips)} devices",
                        progress_percent,
                        completed,
                        len(found_ips)
                    )
                    
                    if completed % 25 == 0:  # Log progress every 25 IPs
                        logger.info(f"Scanned {completed}/{len(host_ips)} IPs...")
                        
                except Exception as e:
                    logger.debug(f"Scan timeout/error for {ip}: {e}")
                    completed += 1
        
        update_scan_progress(f"Scan completed - Found {len(found_ips)} devices", 100, completed, len(found_ips))
        logger.info(f"Network scan completed. Found {len(found_ips)} potential devices out of {len(host_ips)} IPs scanned.")
    
    except Exception as e:
        logger.error(f"Network scanning error: {e}")
        update_scan_progress(f"Scan error: {str(e)}", 0)
    
    return found_ips

def get_host_network_interfaces():
    """Get network interfaces from the host system (works in Docker)."""
    host_networks = []
    wemo_networks = []  # Networks where we can reach WeMo devices
    
    try:
        # Try to detect common host network ranges
        # These are typical ranges used by home routers and corporate networks
        common_host_ranges = [
            '192.168.16.0/24',  # User's network range (prioritize this)
            '192.168.1.0/24',   # Most common home router range
            '192.168.0.0/24',   # Second most common
            '10.0.0.0/24',      # Corporate networks
            '10.0.1.0/24',      # Corporate networks  
            '172.16.0.0/24',    # Corporate networks
            '192.168.2.0/24',   # Other home ranges
            '192.168.10.0/24',
            '192.168.11.0/24',
            '192.168.20.0/24',
            '192.168.50.0/24',
            '192.168.100.0/24',
        ]
        
        # First, test for WeMo devices in each network range
        for range_str in common_host_ranges:
            try:
                network = ipaddress.IPv4Network(range_str, strict=False)
                
                # Test a few common WeMo device IPs in this network
                test_ips = [
                    str(network.network_address + 169),  # .169 (user's device)
                    str(network.network_address + 100),  # .100
                    str(network.network_address + 101),  # .101
                    str(network.network_address + 150),  # .150
                ]
                
                found_wemo_in_network = False
                for test_ip in test_ips:
                    try:
                        # Quick test for WeMo port 49153
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(2)
                        result = sock.connect_ex((test_ip, 49153))
                        sock.close()
                        
                        if result == 0:  # WeMo device found!
                            wemo_networks.append(range_str)
                            logger.info(f"Found WeMo device at {test_ip} in network {range_str}")
                            found_wemo_in_network = True
                            break
                    except Exception:
                        continue
                
                # If we found WeMo devices, this network is high priority
                if found_wemo_in_network:
                    continue
                
                # Otherwise, test gateway connectivity as fallback
                gateway_ip = str(network.network_address + 1)  # Usually .1 is gateway
                
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((gateway_ip, 80))  # Try HTTP port
                sock.close()
                
                # Also try common router admin ports
                if result != 0:
                    sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock2.settimeout(1)
                    result2 = sock2.connect_ex((gateway_ip, 443))  # Try HTTPS
                    sock2.close()
                    if result2 == 0 or result2 == 61:  # Connected or conn refused
                        result = result2
                
                if result == 0 or result == 61:  # Reachable
                    host_networks.append(range_str)
                    logger.info(f"Detected reachable host network: {range_str}")
                    
            except Exception as e:
                logger.debug(f"Failed testing host network {range_str}: {e}")
                continue
        
        # Prioritize networks with WeMo devices, then other reachable networks
        all_networks = wemo_networks + [n for n in host_networks if n not in wemo_networks]
        return all_networks
        
    except Exception as e:
        logger.error(f"Error detecting host networks: {e}")
        return []

def get_local_network_range():
    """Get the local network range for scanning."""
    
    # Method 1: Check if we're in Docker and try to detect host networks
    try:
        # Check if we're running in Docker
        if os.path.exists('/.dockerenv'):
            logger.info("Running in Docker container, detecting host networks...")
            host_networks = get_host_network_interfaces()
            if host_networks:
                # Return the first detected host network
                chosen_network = host_networks[0]
                logger.info(f"Selected host network for scanning: {chosen_network}")
                return chosen_network
        else:
            logger.info("Running on host system, using standard detection...")
    except Exception as e:
        logger.debug(f"Docker detection failed: {e}")
    
    # Method 2: Try to get our own IP and derive network range
    try:
        # Get our container's IP by connecting to a remote address
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            logger.info(f"Detected local IP: {local_ip}")
            
            # If it's a Docker bridge IP (172.x.x.x), try to find host networks
            if local_ip.startswith('172.'):
                logger.info("Detected Docker bridge network, looking for host networks...")
                host_networks = get_host_network_interfaces()
                if host_networks:
                    chosen_network = host_networks[0]
                    logger.info(f"Using host network instead of Docker bridge: {chosen_network}")
                    return chosen_network
            
            # Convert to network range (assume /24)
            ip_parts = local_ip.split('.')
            network_base = '.'.join(ip_parts[:-1]) + '.0/24'
            logger.info(f"Derived network range: {network_base}")
            return network_base
    except Exception as e:
        logger.error(f"Failed to get local IP: {e}")
    
    # Method 2: Try using ip route command (more common in containers)
    try:
        result = subprocess.run(['ip', 'route', 'show', 'default'], 
                              capture_output=True, text=True, timeout=5)
        for line in result.stdout.split('\n'):
            if 'default via' in line:
                parts = line.split()
                gateway_ip = parts[2]  # "default via <IP> dev ..."
                # Assume /24 network
                network_base = '.'.join(gateway_ip.split('.')[:-1]) + '.0/24'
                logger.info(f"Found gateway via ip route: {gateway_ip}, network: {network_base}")
                return network_base
    except Exception as e:
        logger.debug(f"ip route failed: {e}")
    
    # Method 3: Try legacy route command
    try:
        result = subprocess.run(['route', 'get', 'default'], 
                              capture_output=True, text=True, timeout=5)
        for line in result.stdout.split('\n'):
            if 'gateway:' in line:
                gateway = line.split('gateway:')[1].strip()
                network_base = '.'.join(gateway.split('.')[:-1]) + '.0/24'
                logger.info(f"Found gateway via route: {gateway}, network: {network_base}")
                return network_base
    except Exception as e:
        logger.debug(f"route command failed: {e}")
    
    # Method 4: Smart fallback - test common ranges
    logger.info("Trying smart fallback network detection...")
    common_ranges = [
        '192.168.1.0/24',
        '192.168.0.0/24',
        '10.0.0.0/24', 
        '172.16.0.0/24',
        '172.17.0.0/24',  # Common Docker bridge network
        '172.18.0.0/24',  # Docker compose networks
        '172.19.0.0/24',
        '172.20.0.0/24'
    ]
    
    for range_addr in common_ranges:
        try:
            logger.debug(f"Testing network range: {range_addr}")
            # Test if we can reach the gateway of this network
            network = ipaddress.IPv4Network(range_addr, strict=False)
            gateway_ip = str(network.network_address + 1)  # Usually .1 is gateway
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((gateway_ip, 80))  # Try HTTP port
            sock.close()
            
            # Also try ping-like connectivity test
            if result != 0:
                sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock2.settimeout(1)
                result2 = sock2.connect_ex((gateway_ip, 443))  # Try HTTPS port
                sock2.close()
                if result2 == 0 or result2 == 61:  # Connection refused means host is reachable
                    result = result2
            
            if result == 0 or result == 61:  # Connected or connection refused (but reachable)
                logger.info(f"Successfully detected network range: {range_addr}")
                return range_addr
        except Exception as e:
            logger.debug(f"Failed testing range {range_addr}: {e}")
            continue
    
    logger.warning("Could not detect network range, using default 192.168.1.0/24")
    return '192.168.1.0/24'

def check_wemo_port(ip, timeout=2):
    """Check if an IP has WeMo service running on port 49153."""
    try:
        # First, check if port 49153 is open
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, 49153))
        sock.close()
        
        if result == 0:
            # Port is open, now try to verify it's actually a WeMo device
            try:
                import urllib.request
                import urllib.error
                
                # Try to get the setup.xml file that WeMo devices serve
                url = f"http://{ip}:49153/setup.xml"
                req = urllib.request.Request(url)
                req.add_header('User-Agent', 'PyWemo-API/1.0')
                
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    content = response.read().decode('utf-8', errors='ignore')
                    # Check if this looks like a WeMo device
                    if any(keyword in content.lower() for keyword in ['wemo', 'belkin', 'urn:belkin']):
                        logger.info(f"🎉 Confirmed WeMo device at {ip} (found WeMo signatures in setup.xml)")
                        return True
                    else:
                        logger.debug(f"Port 49153 open at {ip} but doesn't appear to be WeMo device")
                        return False
            except Exception as e:
                # If HTTP fails but port was open, might still be WeMo
                logger.debug(f"HTTP check failed for {ip}, but port was open: {e}")
                return True  # Give benefit of doubt if port is open
        
        return False
    except Exception as e:
        logger.debug(f"Port check failed for {ip}: {e}")
        return False

def refresh_known_devices():
    """Refresh connection to known devices to ensure they're still available."""
    to_remove = []
    for udn, device in list(device_map.items()):
        try:
            # Try to get device state to verify it's still reachable
            if hasattr(device, 'get_state'):
                device.get_state()
        except Exception as e:
            logger.warning(f"Device {device.name} ({udn}) may be offline: {e}")
            # Don't remove immediately, just log the issue

def background_discovery_worker():
    """Background thread for periodic device discovery."""
    global discovery_status
    
    discovery_status["background_discovery_running"] = True
    logger.info("Background discovery worker started")
    
    while discovery_status["auto_discovery_enabled"]:
        try:
            time.sleep(300)  # Wait 5 minutes between discoveries
            if discovery_status["auto_discovery_enabled"]:
                logger.info("Running background device discovery")
                discover_devices_enhanced(timeout=15, network_scan=True)
        except Exception as e:
            logger.error(f"Background discovery error: {e}")
            time.sleep(60)  # Wait 1 minute before retrying on error
    
    discovery_status["background_discovery_running"] = False
    logger.info("Background discovery worker stopped")

# Initialize friendly names storage
load_friendly_names()

# Start initial discovery and background worker
# Use shorter timeout for initial startup to avoid hanging - disable network scan for fast startup
discover_devices_enhanced(timeout=3, network_scan=False)

# Start background discovery thread
background_thread = threading.Thread(target=background_discovery_worker, daemon=True)
background_thread.start()

# Serve the web interface
@app.route("/")
def index():
    return send_from_directory('static', 'index.html')

@app.route("/web")
def web_interface():
    return redirect(url_for('index'))

# Discover Wemo devices by IP address (supports multiple IPs)
@app.route("/device/discover_by_ip", methods=["POST"])
def discover_by_ip():
    data = request.get_json()
    if not data or "ip" not in data:
        abort(400, description="Missing 'ip' in request body")
    
    ip_input = data["ip"].strip()
    if not ip_input:
        abort(400, description="IP address cannot be empty")
    
    # Parse multiple IP addresses separated by spaces, commas, or semicolons
    import re
    ip_list = re.split(r'[\s,;]+', ip_input)
    ip_list = [ip.strip() for ip in ip_list if ip.strip()]
    
    if not ip_list:
        abort(400, description="No valid IP addresses provided")
    
    results = []
    newly_discovered = 0
    already_existed = 0
    failed = 0
    
    for ip in ip_list:
        # Basic IP validation
        if not re.match(r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$', ip):
            results.append({
                "ip": ip,
                "success": False,
                "error": "Invalid IP address format",
                "message": f"'{ip}' is not a valid IP address"
            })
            failed += 1
            continue
        
        setup_url = f"http://{ip}:49153/setup.xml"
        try:
            device = pywemo.discovery.device_from_description(setup_url)
            if device:
                # Check if device already exists
                if device.udn in device_map:
                    results.append({
                        "ip": ip,
                        "success": True,
                        "name": device.name,
                        "model": getattr(device, "model_name", None),
                        "udn": getattr(device, "udn", None),
                        "serial": getattr(device, "serialnumber", None),
                        "ip_address": getattr(device, "host", None),
                        "already_discovered": True,
                        "message": f"Device '{device.name}' was already discovered"
                    })
                    already_existed += 1
                else:
                    # Add new device
                    device_map[device.udn] = device
                    devices.append(device)
                    results.append({
                        "ip": ip,
                        "success": True,
                        "name": device.name,
                        "model": getattr(device, "model_name", None),
                        "udn": getattr(device, "udn", None),
                        "serial": getattr(device, "serialnumber", None),
                        "ip_address": getattr(device, "host", None),
                        "already_discovered": False,
                        "message": f"Device '{device.name}' discovered and added successfully"
                    })
                    newly_discovered += 1
            else:
                results.append({
                    "ip": ip,
                    "success": False,
                    "error": "No device found",
                    "message": f"No WeMo device found at {ip}"
                })
                failed += 1
        except Exception as e:
            results.append({
                "ip": ip,
                "success": False,
                "error": str(e),
                "message": f"Error discovering device at {ip}: {str(e)}"
            })
            failed += 1
    
    # Generate summary message
    total_ips = len(ip_list)
    summary_parts = []
    if newly_discovered > 0:
        summary_parts.append(f"{newly_discovered} new device{'s' if newly_discovered != 1 else ''} added")
    if already_existed > 0:
        summary_parts.append(f"{already_existed} device{'s' if already_existed != 1 else ''} already known")
    if failed > 0:
        summary_parts.append(f"{failed} failed")
    
    summary = ", ".join(summary_parts)
    
    return jsonify({
        "total_ips_processed": total_ips,
        "newly_discovered": newly_discovered,
        "already_existed": already_existed,
        "failed": failed,
        "summary": f"Processed {total_ips} IP{'s' if total_ips != 1 else ''}: {summary}",
        "results": results
    })

@app.route("/devices", methods=["GET"])
def list_devices():
    # List discovered devices with friendly name support
    return jsonify([
        get_device_info_with_friendly_name(device)
        for device in devices
    ])

# Forget/remove a device
@app.route("/device/<udn>/forget", methods=["POST", "DELETE"])
def forget_device(udn):
    """Remove a device from the discovered devices list."""
    global devices, device_map
    
    if udn not in device_map:
        abort(404, description="Device not found")
    
    device = device_map[udn]
    device_info = {
        "name": device.name,
        "model": getattr(device, "model_name", None),
        "udn": device.udn,
        "serial": getattr(device, "serialnumber", None),
        "ip_address": getattr(device, "host", None)
    }
    
    # Remove from both data structures
    del device_map[udn]
    devices = [d for d in devices if d.udn != udn]
    
    logger.info(f"Device forgotten: {device.name} ({udn})")
    
    return jsonify({
        "message": "Device forgotten successfully",
        "device": device_info,
        "remaining_devices": len(devices)
    })

# Forget all devices
@app.route("/devices/forget_all", methods=["POST", "DELETE"])
def forget_all_devices():
    """Remove all devices from the discovered devices list."""
    global devices, device_map, friendly_names
    
    forgotten_count = len(devices)
    forgotten_devices = [
        {
            "name": device.name,
            "model": getattr(device, "model_name", None),
            "udn": device.udn,
            "ip_address": getattr(device, "host", None)
        }
        for device in devices
    ]
    
    # Also remove friendly names for forgotten devices
    device_udns = {device.udn for device in devices}
    for udn in device_udns:
        if udn in friendly_names:
            del friendly_names[udn]
    
    # Clear both data structures
    devices.clear()
    device_map.clear()
    
    # Save updated friendly names
    save_friendly_names()
    
    logger.info(f"All devices forgotten: {forgotten_count} devices removed")
    
    return jsonify({
        "message": f"All {forgotten_count} devices forgotten successfully",
        "forgotten_devices": forgotten_devices,
        "remaining_devices": 0
    })

# Friendly device name management endpoints
@app.route("/device/<udn>/friendly-name", methods=["GET"])
def get_device_friendly_name(udn):
    """Get the friendly name for a device."""
    if udn not in device_map:
        abort(404, description="Device not found")
    
    device = device_map[udn]
    return jsonify({
        "udn": udn,
        "original_name": device.name,
        "friendly_name": friendly_names.get(udn),
        "display_name": get_device_display_name(device)
    })

@app.route("/device/<udn>/friendly-name", methods=["POST", "PUT"])
def set_device_friendly_name(udn):
    """Set or update the friendly name for a device."""
    if udn not in device_map:
        abort(404, description="Device not found")
    
    data = request.get_json()
    if not data or "friendly_name" not in data:
        abort(400, description="Missing 'friendly_name' in request body")
    
    friendly_name = data["friendly_name"].strip() if data["friendly_name"] else None
    device = device_map[udn]
    
    if friendly_name:
        friendly_names[udn] = friendly_name
        message = "Friendly name set successfully"
    else:
        # Remove friendly name if empty
        if udn in friendly_names:
            del friendly_names[udn]
        message = "Friendly name removed successfully"
    
    # Save to file
    save_friendly_names()
    
    logger.info(f"Friendly name updated for {device.name}: {friendly_name}")
    
    return jsonify({
        "message": message,
        "udn": udn,
        "original_name": device.name,
        "friendly_name": friendly_names.get(udn),
        "display_name": get_device_display_name(device)
    })

@app.route("/device/<udn>/friendly-name", methods=["DELETE"])
def delete_device_friendly_name(udn):
    """Remove the friendly name for a device."""
    if udn not in device_map:
        abort(404, description="Device not found")
    
    device = device_map[udn]
    
    if udn in friendly_names:
        del friendly_names[udn]
        save_friendly_names()
        message = "Friendly name removed successfully"
    else:
        message = "Device had no friendly name to remove"
    
    logger.info(f"Friendly name removed for {device.name}")
    
    return jsonify({
        "message": message,
        "udn": udn,
        "original_name": device.name,
        "friendly_name": None,
        "display_name": device.name
    })


@app.route("/devices/refresh", methods=["POST"])
def refresh_devices():
    """Enhanced refresh with optional network scanning and custom network range."""
    data = request.get_json() if request.is_json else {}
    network_scan = data.get("network_scan", False)
    timeout = data.get("timeout", 10)
    custom_network = data.get("custom_network")
    
    # Validate custom network if provided
    if custom_network:
        is_valid, normalized_network, error_msg = validate_network_range(custom_network)
        if not is_valid:
            abort(400, description=f"Invalid network range: {error_msg}")
        custom_network = normalized_network
    
    count = discover_devices_enhanced(timeout=timeout, network_scan=network_scan, custom_network=custom_network)
    return jsonify({
        "status": "refreshed", 
        "count": count,
        "network_scan": network_scan,
        "timeout": timeout,
        "custom_network": custom_network,
        "discovery_time": discovery_status["last_discovery"]
    })

@app.route("/devices/discovery/status", methods=["GET"])
def get_discovery_status():
    """Get current discovery system status."""
    return jsonify({
        **discovery_status,
        "device_count": len(devices),
        "last_discovery_formatted": time.strftime("%Y-%m-%d %H:%M:%S", 
                                                 time.localtime(discovery_status["last_discovery"])) 
                                   if discovery_status["last_discovery"] else None
    })

@app.route("/devices/discovery/network-scan", methods=["POST"])
def trigger_network_scan():
    """Trigger a comprehensive network scan for WeMo devices with optional custom network range."""
    global scan_progress
    
    # Check if already scanning
    if scan_progress["is_scanning"]:
        return jsonify({
            "error": "Scan already in progress",
            "current_scan": {
                "scan_type": scan_progress["scan_type"],
                "progress_percent": scan_progress["progress_percent"],
                "current_step": scan_progress["current_step"]
            }
        }), 409  # Conflict
    
    data = request.get_json() if request.is_json else {}
    timeout = data.get("timeout", 15)
    custom_network = data.get("custom_network")
    
    # Validate custom network if provided
    if custom_network:
        is_valid, normalized_network, error_msg = validate_network_range(custom_network)
        if not is_valid:
            abort(400, description=f"Invalid network range: {error_msg}")
        custom_network = normalized_network
        logger.info(f"Manual network scan triggered for custom range: {custom_network}")
    else:
        logger.info("Manual network scan triggered via API")
    
    # Start progress tracking
    start_scan_progress("network", custom_network)
    
    try:
        count = discover_devices_enhanced(timeout=timeout, network_scan=True, custom_network=custom_network)
        
        return jsonify({
            "status": "network_scan_completed",
            "devices_found": count,
            "scan_timeout": timeout,
            "custom_network": custom_network,
            "scan_progress_id": "network_scan"
        })
    except Exception as e:
        # Ensure progress tracking is cleared on error
        finish_scan_progress()
        raise

@app.route("/devices/scan/progress", methods=["GET"])
def get_scan_progress():
    """Get current scan progress status."""
    global scan_progress
    
    response_data = dict(scan_progress)
    
    # Format estimated time remaining
    if response_data["estimated_time_remaining"] > 0:
        remaining = response_data["estimated_time_remaining"]
        if remaining < 60:
            response_data["estimated_time_remaining_formatted"] = f"{remaining:.1f}s"
        elif remaining < 3600:
            response_data["estimated_time_remaining_formatted"] = f"{remaining/60:.1f}m"
        else:
            response_data["estimated_time_remaining_formatted"] = f"{remaining/3600:.1f}h"
    else:
        response_data["estimated_time_remaining_formatted"] = None
    
    # Add elapsed time
    if scan_progress["start_time"]:
        elapsed = time.time() - scan_progress["start_time"]
        response_data["elapsed_time"] = elapsed
        if elapsed < 60:
            response_data["elapsed_time_formatted"] = f"{elapsed:.1f}s"
        elif elapsed < 3600:
            response_data["elapsed_time_formatted"] = f"{elapsed/60:.1f}m"
        else:
            response_data["elapsed_time_formatted"] = f"{elapsed/3600:.1f}h"
    else:
        response_data["elapsed_time"] = 0
        response_data["elapsed_time_formatted"] = "0s"
    
    return jsonify(response_data)

@app.route("/devices/scan/cancel", methods=["POST"])
def cancel_scan():
    """Cancel current scan operation."""
    global scan_progress
    
    if not scan_progress["is_scanning"]:
        return jsonify({
            "error": "No scan in progress"
        }), 400
    
    if not scan_progress["can_cancel"]:
        return jsonify({
            "error": "Current scan cannot be cancelled"
        }), 400
    
    # Mark scan as cancelled
    scan_progress["is_scanning"] = False
    scan_progress["current_step"] = "Cancelling scan..."
    
    logger.info(f"Scan cancelled by user: {scan_progress['scan_type']}")
    
    # Clean up progress after a short delay
    def cleanup_progress():
        time.sleep(2)
        finish_scan_progress()
        scan_progress["current_step"] = "Scan cancelled"
    
    import threading
    threading.Thread(target=cleanup_progress, daemon=True).start()
    
    return jsonify({
        "status": "scan_cancelled",
        "message": "Scan cancellation initiated"
    })

@app.route("/devices/bulk/turn_on", methods=["POST"])
def turn_all_devices_on():
    """Turn on all discovered devices."""
    if not devices:
        return jsonify({
            "error": "No devices available",
            "message": "No devices have been discovered yet"
        }), 400
    
    results = []
    success_count = 0
    error_count = 0
    
    logger.info(f"Turning on all {len(devices)} devices")
    
    for device in devices:
        device_info = {
            "name": device.name,
            "udn": device.udn,
            "model": getattr(device, "model_name", None),
            "ip_address": getattr(device, "host", None)
        }
        
        try:
            # Check if device has an 'on' method
            if hasattr(device, 'on') and callable(getattr(device, 'on')):
                device.on()
                device_info["status"] = "success"
                device_info["message"] = "Device turned on successfully"
                success_count += 1
                logger.info(f"Successfully turned on {device.name}")
            else:
                device_info["status"] = "skipped"
                device_info["message"] = "Device does not support on/off control"
                logger.warning(f"Device {device.name} does not support on/off control")
                
        except Exception as e:
            device_info["status"] = "error"
            device_info["message"] = str(e)
            error_count += 1
            logger.error(f"Failed to turn on {device.name}: {e}")
        
        results.append(device_info)
    
    return jsonify({
        "message": f"Bulk turn on completed: {success_count} successful, {error_count} failed",
        "summary": {
            "total_devices": len(devices),
            "successful": success_count,
            "failed": error_count,
            "skipped": len(devices) - success_count - error_count
        },
        "results": results
    })

@app.route("/devices/bulk/turn_off", methods=["POST"])
def turn_all_devices_off():
    """Turn off all discovered devices."""
    if not devices:
        return jsonify({
            "error": "No devices available",
            "message": "No devices have been discovered yet"
        }), 400
    
    results = []
    success_count = 0
    error_count = 0
    
    logger.info(f"Turning off all {len(devices)} devices")
    
    for device in devices:
        device_info = {
            "name": device.name,
            "udn": device.udn,
            "model": getattr(device, "model_name", None),
            "ip_address": getattr(device, "host", None)
        }
        
        try:
            # Check if device has an 'off' method
            if hasattr(device, 'off') and callable(getattr(device, 'off')):
                device.off()
                device_info["status"] = "success"
                device_info["message"] = "Device turned off successfully"
                success_count += 1
                logger.info(f"Successfully turned off {device.name}")
            else:
                device_info["status"] = "skipped"
                device_info["message"] = "Device does not support on/off control"
                logger.warning(f"Device {device.name} does not support on/off control")
                
        except Exception as e:
            device_info["status"] = "error"
            device_info["message"] = str(e)
            error_count += 1
            logger.error(f"Failed to turn off {device.name}: {e}")
        
        results.append(device_info)
    
    return jsonify({
        "message": f"Bulk turn off completed: {success_count} successful, {error_count} failed",
        "summary": {
            "total_devices": len(devices),
            "successful": success_count,
            "failed": error_count,
            "skipped": len(devices) - success_count - error_count
        },
        "results": results
    })

@app.route("/devices/status", methods=["GET"])
def get_devices_status():
    """Get current status of all discovered devices in an efficient batch call.
    
    This endpoint is optimized for periodic polling to update the UI with current
    device states without requiring individual API calls for each device.
    """
    if not devices:
        return jsonify({
            "devices": [],
            "summary": {
                "total": 0,
                "online": 0,
                "offline": 0,
                "unknown": 0
            },
            "timestamp": time.time()
        })
    
    device_statuses = []
    online_count = 0
    offline_count = 0
    unknown_count = 0
    
    # Use ThreadPoolExecutor for parallel status checking
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Submit all status check tasks
        future_to_device = {
            executor.submit(get_device_status_info, device): device 
            for device in devices
        }
        
        # Collect results as they complete with proper timeout handling
        try:
            for future in as_completed(future_to_device, timeout=15):
                device = future_to_device[future]
                try:
                    device_status = future.result(timeout=8)
                    device_statuses.append(device_status)
                    
                    # Count status types
                    if device_status['connection_status'] == 'online':
                        online_count += 1
                    elif device_status['connection_status'] == 'offline':
                        offline_count += 1
                    else:
                        unknown_count += 1
                        
                except Exception as e:
                    # Fallback for failed status checks
                    logger.debug(f"Failed to get status for device {device.name}: {e}")
                    device_status = {
                        "name": device.name,
                        "udn": device.udn,
                        "model": getattr(device, "model_name", "Unknown"),
                        "ip_address": getattr(device, "host", None),
                        "state": "unknown",
                        "connection_status": "offline",
                        "last_seen": None,
                        "error": str(e)
                    }
                    device_statuses.append(device_status)
                    offline_count += 1
        except TimeoutError:
            # Handle the case where some futures didn't complete in time
            logger.warning("Some device status checks timed out")
            
            # Process any remaining unfinished futures as offline
            for future, device in future_to_device.items():
                if not future.done():
                    logger.debug(f"Device {device.name} status check timed out, marking as offline")
                    device_status = {
                        "name": device.name,
                        "udn": device.udn,
                        "model": getattr(device, "model_name", "Unknown"),
                        "ip_address": getattr(device, "host", None),
                        "state": "unknown",
                        "connection_status": "offline",
                        "last_seen": None,
                        "error": "Connection timeout"
                    }
                    device_statuses.append(device_status)
                    offline_count += 1
                    
                    # Cancel the remaining future to clean up
                    future.cancel()
    
    return jsonify({
        "devices": device_statuses,
        "summary": {
            "total": len(devices),
            "online": online_count,
            "offline": offline_count,
            "unknown": unknown_count
        },
        "timestamp": time.time()
    })

def get_device_status_info(device, timeout=5):
    """Get comprehensive status information for a single device with timeout control."""
    device_info = {
        "name": device.name,
        "udn": device.udn,
        "model": getattr(device, "model_name", "Unknown"),
        "ip_address": getattr(device, "host", None),
        "state": "unknown",
        "connection_status": "unknown",
        "last_seen": time.time()
    }
    
    try:
        # Try to get device state - force fresh query by clearing all possible caches
        if hasattr(device, 'get_state'):
            # Clear all known PyWemo caching mechanisms
            clear_device_cache(device)
            
            # Try multiple approaches to get fresh state
            state = None
            
            # Method 1: Try get_state with force_update parameter
            try:
                if 'force_update' in inspect.signature(device.get_state).parameters:
                    state = device.get_state(force_update=True)
            except (TypeError, AttributeError):
                pass
            
            # Method 2: Standard get_state after cache clearing
            if state is None:
                try:
                    state = device.get_state()
                except Exception as e:
                    logger.debug(f"get_state failed: {e}")
            
            # Method 3: Direct SOAP call if available
            if state is None and hasattr(device, 'basicevent'):
                try:
                    # Force a direct SOAP call
                    state_response = device.basicevent.GetBinaryState()
                    state = int(state_response.get('BinaryState', 0))
                except Exception as e:
                    logger.debug(f"Direct SOAP call failed: {e}")
            
            # Method 4: Last resort - assume offline if all methods fail
            if state is None:
                logger.warning(f"All state query methods failed for device {device.name}")
                raise Exception("Unable to determine device state")
                
            device_info["state"] = "on" if state == 1 else "off" if state == 0 else "unknown"
            device_info["connection_status"] = "online"
        else:
            # For devices without get_state, try another method to check connectivity
            if hasattr(device, 'basicevent'):
                # Try to access a basic property
                device.basicevent.GetFriendlyName()
                device_info["connection_status"] = "online"
            else:
                device_info["connection_status"] = "unknown"
                
    except Exception as e:
        # Device is likely offline or unreachable
        device_info["connection_status"] = "offline"
        device_info["error"] = str(e)
        logger.debug(f"Device {device.name} appears offline: {e}")
    
    return device_info

@app.route("/devices/discovery/toggle", methods=["POST"])
def toggle_auto_discovery():
    """Enable/disable automatic background discovery."""
    global discovery_status
    
    data = request.get_json() if request.is_json else {}
    enable = data.get("enable", not discovery_status["auto_discovery_enabled"])
    
    discovery_status["auto_discovery_enabled"] = enable
    
    return jsonify({
        "auto_discovery_enabled": discovery_status["auto_discovery_enabled"],
        "background_discovery_running": discovery_status["background_discovery_running"]
    })

@app.route("/devices/discovery/debug", methods=["GET"])
def debug_network_detection():
    """Debug endpoint to test network detection."""
    debug_info = {}
    
    # Check if running in Docker
    debug_info["running_in_docker"] = os.path.exists('/.dockerenv')
    
    try:
        # Test local IP detection
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            debug_info["local_ip"] = local_ip
            debug_info["is_docker_bridge_ip"] = local_ip.startswith('172.')
    except Exception as e:
        debug_info["local_ip_error"] = str(e)
    
    # Test host network detection (for Docker)
    try:
        host_networks = get_host_network_interfaces()
        debug_info["detected_host_networks"] = host_networks
        debug_info["priority_network_explanation"] = "Networks are ordered by priority: WeMo-accessible networks first, then other reachable networks"
    except Exception as e:
        debug_info["host_network_error"] = str(e)
    
    # Test network range detection
    try:
        network_range = get_local_network_range()
        debug_info["detected_network_range"] = network_range
        
        if network_range:
            network = ipaddress.IPv4Network(network_range, strict=False)
            debug_info["network_info"] = {
                "network_address": str(network.network_address),
                "broadcast_address": str(network.broadcast_address),
                "total_hosts": len(list(network.hosts())),
                "first_host": str(list(network.hosts())[0]) if list(network.hosts()) else None,
                "last_host": str(list(network.hosts())[-1]) if list(network.hosts()) else None
            }
    except Exception as e:
        debug_info["network_range_error"] = str(e)
    
    # Test connectivity to discovered WeMo devices
    debug_info["wemo_device_tests"] = {}
    if devices:
        # Test first few discovered devices
        for device in devices[:3]:
            device_ip = getattr(device, "host", None)
            if device_ip:
                try:
                    # Test WeMo port specifically
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(3)
                    result = sock.connect_ex((device_ip, 49153))  # WeMo port
                    sock.close()
                    debug_info["wemo_device_tests"][f"{device_ip}:49153"] = {
                        "reachable": result == 0,
                        "connect_result": result,
                        "device_name": device.name
                    }
                except Exception as e:
                    debug_info["wemo_device_tests"][f"{device_ip}:49153"] = {
                        "error": str(e),
                        "device_name": device.name
                    }
    
    # Test a few gateway IPs manually
    test_ips = ["192.168.1.1", "192.168.0.1", "192.168.16.1", "10.0.0.1"]
    debug_info["gateway_tests"] = {}
    
    for test_ip in test_ips:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((test_ip, 80))
            sock.close()
            debug_info["gateway_tests"][test_ip] = {
                "reachable": result == 0 or result == 61,
                "connect_result": result
            }
        except Exception as e:
            debug_info["gateway_tests"][test_ip] = {"error": str(e)}
    
    return jsonify(debug_info)

@app.route("/devices/network/validate", methods=["POST"])
def validate_network_endpoint():
    """Validate a network range and return information about it."""
    data = request.get_json()
    if not data or "network" not in data:
        abort(400, description="Missing 'network' in request body")
    
    network_input = data["network"]
    is_valid, normalized_network, error_msg = validate_network_range(network_input)
    
    if not is_valid:
        return jsonify({
            "valid": False,
            "error": error_msg,
            "input": network_input
        }), 400
    
    # Get network information
    network_info = get_network_scan_info(normalized_network)
    
    return jsonify({
        "valid": True,
        "input": network_input,
        "normalized": normalized_network,
        "info": network_info
    })

@app.route("/device/<udn>/methods", methods=["GET"])
def get_methods(udn):
    device = device_map.get(udn)
    if not device:
        abort(404, description="Device not found")
    # Get public methods
    methods = [
        name for name, member in inspect.getmembers(device, predicate=inspect.ismethod)
        if not name.startswith("_")
    ]
    return jsonify(methods)

@app.route("/device/<udn>/<method>", methods=["POST", "GET"])
def call_method(udn, method):
    device = device_map.get(udn)
    if not device:
        abort(404, description="Device not found")

    # Check if method exists and is public
    if not hasattr(device, method) or method.startswith("_"):
        abort(404, description="Method not found")

    func = getattr(device, method)
    if not inspect.ismethod(func):
        abort(404, description="Not a method")

    # Arguments via JSON
    args = request.json.get("args", []) if request.is_json else []
    kwargs = request.json.get("kwargs", {}) if request.is_json else {}

    try:
        # For state-related methods, clear cache to ensure fresh data
        if method in ['get_state', 'toggle', 'on', 'off']:
            clear_device_cache(device)
                
        result = func(*args, **kwargs)
        
        # For state-changing methods, also clear cache after execution
        if method in ['toggle', 'on', 'off']:
            clear_device_cache(device)
        
        # If result is a pywemo device, convert to dict
        if hasattr(result, "name"):
            result = {
                "name": result.name,
                "model": getattr(result, "model_name", None),
                "udn": getattr(result, "udn", None),
                "serial": getattr(result, "serialnumber", None)
            }
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": str(e)}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
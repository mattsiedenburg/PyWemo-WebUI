# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

PyWemo-WebUI is a Flask-based REST API that provides HTTP access to Belkin WeMo smart home devices using the [pywemo](https://github.com/pywemo/pywemo) library. It features both a REST API and a modern web interface for controlling WeMo devices.

**Important Context**: This codebase is self-described as "vibe coded" using GitHub Copilot and ChatGPT, prioritizing functionality over perfect code structure. The author acknowledges it may be "the worst, ugliest, buggiest, most inefficient, most insecure implementation" but it works for basic WeMo smart plugs.

## Development Commands

### Quick Start
```bash
# Using Docker Compose (recommended)
docker-compose up -d

# Manual setup
pip install -r requirements.txt
python app.py

# Development mode
FLASK_ENV=development python app.py
```

### Testing
```bash
# Run comprehensive test suite
python scripts/test_pywemo_api.py

# Test specific functionality  
python scripts/test_manual_changes.py
python scripts/test_offline_detection.py
python scripts/test_realtime_monitoring.py
```

### Docker Operations
```bash
# Build and run with Docker
docker build -t pywemo-api .
docker run -p 5000:5000 pywemo-api

# Rebuild with status monitoring fix
./scripts/rebuild_with_status_fix.sh
```

## Code Architecture

### Core Components

**Flask Application (`app.py`)**
- Single-file Flask application (~1600 lines)
- Handles both REST API endpoints and web interface serving
- Uses global state for device management (not thread-safe by design)
- Implements extensive device discovery and caching mechanisms

**Key Global State**:
- `devices[]`: List of discovered WeMo devices
- `device_map{}`: Maps device UDN (Unique Device Name) to device instances  
- `discovery_status{}`: Tracks discovery system state
- `scan_progress{}`: Tracks network scanning progress
- `friendly_names{}`: Maps device UDN to user-friendly names

**Web Interface (`static/index.html`)**
- Single-page application with vanilla JavaScript
- Real-time device status monitoring with auto-refresh
- Theme switching (light/dark/auto)
- Progress tracking for network scans

### Device Discovery Architecture

The application uses a multi-layered discovery approach:

1. **Standard UPnP Discovery**: Uses `pywemo.discover_devices()`
2. **Network Scanning**: Concurrent scanning of IP ranges for port 49153 (WeMo port)
3. **Manual IP Discovery**: Direct device addition by IP address
4. **Background Discovery**: Periodic re-discovery every 5 minutes
5. **Cache Management**: Aggressive cache clearing for fresh device state queries

**Network Detection**:
- Docker-aware network detection
- Tests common home network ranges (192.168.x.x, 10.x.x.x, 172.x.x.x)
- Prioritizes networks where WeMo devices are actually found
- Supports custom network ranges in CIDR notation

### Device State Management

**Cache Clearing Strategy**: The app implements aggressive cache clearing because PyWemo library caches device states, which interferes with real-time monitoring. See `clear_device_cache()` function which clears:
- Direct device state caches (`_state`, `_cached_state`)
- BasicEvent service caches  
- SOAP service caches
- Any cached attributes on device objects

**Status Monitoring**: Uses ThreadPoolExecutor for parallel device status checks with proper timeout handling. Implements multiple fallback methods for getting device state when the primary `get_state()` method fails.

## Key REST API Endpoints

### Device Management
- `GET /devices` - List all discovered devices with friendly names
- `POST /devices/refresh` - Refresh device list with optional network scan
- `POST /device/discover_by_ip` - Add device(s) by IP address (supports multiple IPs)
- `POST /device/{udn}/forget` - Remove device from discovered list
- `DELETE /devices/forget_all` - Remove all devices

### Device Control  
- `GET /device/{udn}/methods` - Get available methods for device
- `POST /device/{udn}/{method}` - Execute method on device with JSON args
- `GET /devices/status` - Batch status check for all devices (optimized for UI polling)

### Discovery & Scanning
- `POST /devices/discovery/network-scan` - Trigger network scan with progress tracking
- `GET /devices/scan/progress` - Get current scan progress
- `POST /devices/scan/cancel` - Cancel active scan
- `GET /devices/discovery/debug` - Debug network detection (useful for Docker issues)

### Bulk Operations
- `POST /devices/bulk/turn_on` - Turn on all devices
- `POST /devices/bulk/turn_off` - Turn off all devices

## Important Implementation Details

### Docker Network Considerations
The app includes sophisticated Docker network detection because WeMo devices are on the host network while the container runs in an isolated network. The `get_host_network_interfaces()` function:
- Tests common home router IP ranges
- Prioritizes networks where WeMo devices are actually reachable
- Falls back to gateway connectivity tests
- Handles Docker bridge network detection

### Concurrency & Performance  
- Uses `ThreadPoolExecutor` for parallel device operations
- Implements timeouts for all device communication
- Background discovery runs in daemon thread
- Scan progress tracking with real-time updates
- LRU caching for network validation

### Error Handling Philosophy
The code prioritizes functionality over strict error handling. Many operations use broad exception catching with debug logging, allowing the system to continue operating even when individual devices fail.

### Data Persistence
- Friendly device names stored in `/app/data/friendly_names.json`
- No database - all device discovery happens at runtime
- Stateless design (except for friendly names)

## Testing Strategy

The `scripts/test_pywemo_api.py` provides comprehensive API testing including:
- Web interface accessibility
- All REST endpoints  
- Error handling scenarios
- Concurrent request handling
- Network scanning functionality

## Development Notes

### When Working with Device Discovery
- Device caching is the main source of "state not updating" issues
- Always test with actual WeMo hardware when possible
- Network scanning can be slow (~0.1s per IP tested)
- Docker networking issues are common - use debug endpoint to diagnose

### When Working with the Web Interface
- Single HTML file with embedded JavaScript
- Uses vanilla JS (no frameworks)
- Responsive design with CSS Grid
- Real-time updates via periodic API polling (not WebSockets)

### When Adding New Features
- Follow the existing pattern of Flask route + corresponding JavaScript function
- Add comprehensive error handling (follow existing patterns)
- Consider Docker network implications for any network-related features
- Update the test suite in `scripts/test_pywemo_api.py`

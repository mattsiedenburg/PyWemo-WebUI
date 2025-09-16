# PyWemo API

A Flask-based REST API that provides HTTP access to Belkin WeMo smart home devices using the [pywemo](https://github.com/pywemo/pywemo) library.

I know enough Python and Flask to be dangerous but this is 100% "vibe coded" using GitHub Copilot with ChatGPT for the API and Claude Sonnet 4 for the web UI. Please don't ask me for support! ;)

I only have Belkin WeMo smart plugs and it works well enough for these. I can't speak to the functionality of other types of devices.

## Features

- **Device Discovery**: Automatically discover WeMo devices on your network
- **Manual Device Addition**: Add devices by IP address
- **Dynamic Method Calling**: Call any public method on discovered devices via HTTP
- **RESTful Interface**: Simple HTTP API for device control and monitoring
- **Docker Support**: Easy deployment with Docker and Docker Compose

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Clone or download the project
cd pywemo-api

# Start the service
docker-compose up -d
```

The API will be available at `http://localhost:5000`

**🎉 New Web Interface**: Open `http://localhost:5000` in your browser to access the user-friendly web interface for controlling your WeMo devices!

### Manual Setup

1. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application**:
   ```bash
   python app.py
   ```

## Web Interface

PyWemo API now includes a modern, responsive web interface that makes it easy to control your WeMo devices without writing code or using command-line tools.

### Features

- **📱 Responsive Design**: Works on desktop, tablet, and mobile devices
- **🔄 Auto-Discovery**: Automatically finds and displays all WeMo devices on your network
- **🎛️ Device Control**: Easy-to-use interface for controlling any device method
- **➕ Manual Discovery**: Add devices manually by IP address
- **📊 Real-time Status**: Get instant feedback on device operations
- **🔧 Method Explorer**: Browse and execute any available device method with parameters
- **🚫 Duplicate Prevention**: Automatically prevents adding the same device multiple times

### Accessing the Web Interface

1. **Start the PyWemo API** (using Docker Compose or manually)
2. **Open your browser** and navigate to `http://localhost:5000`
3. **Discover devices** by clicking "🔄 Refresh Devices" or add them manually
4. **Control devices** by clicking "🔧 Control Device" on any device card
5. **Execute methods** with optional parameters through the intuitive interface

### Web Interface Screenshots

The web interface provides:
- A clean dashboard showing all discovered devices
- Device cards with name, model, and serial information
- Quick actions like "Get State" for immediate feedback
- A method explorer modal for advanced device control
- Form-based parameter input for methods requiring arguments

## API Endpoints

### Device Management

#### List Devices
```http
GET /devices
```
Returns all discovered WeMo devices.

**Response**:
```json
[
  {
    "name": "Living Room Light",
    "model": "Socket",
    "udn": "uuid:Socket-1_0-221517K0101769",
    "serial": "221517K0101769"
  }
]
```

#### Refresh Device List
```http
POST /devices/refresh
```
Re-discovers all devices on the network.

**Response**:
```json
{
  "status": "refreshed",
  "count": 2
}
```

#### Discover Device by IP
```http
POST /device/discover_by_ip
```
Manually add a device by its IP address.

**Request Body**:
```json
{
  "ip": "192.168.1.100"
}
```

**Response** (new device):
```json
{
  "name": "Living Room Light",
  "model": "Socket",
  "udn": "uuid:Socket-1_0-221517K0101769",
  "serial": "221517K0101769",
  "already_discovered": false,
  "message": "Device discovered and added successfully"
}
```

**Response** (duplicate device):
```json
{
  "name": "Living Room Light",
  "model": "Socket",
  "udn": "uuid:Socket-1_0-221517K0101769",
  "serial": "221517K0101769",
  "already_discovered": true,
  "message": "Device was already discovered"
}
```

### Device Control

#### Get Available Methods
```http
GET /device/{udn}/methods
```
Returns all available public methods for a specific device.

**Response**:
```json
[
  "get_state",
  "on",
  "off",
  "toggle"
]
```

#### Call Device Method
```http
POST /device/{udn}/{method}
GET /device/{udn}/{method}
```
Execute a method on the specified device.

**Request Body** (optional):
```json
{
  "args": [],
  "kwargs": {}
}
```

**Examples**:

Turn on a switch:
```bash
curl -X POST http://localhost:5000/device/uuid:Socket-1_0-221517K0101769/on
```

Get device state:
```bash
curl -X GET http://localhost:5000/device/uuid:Socket-1_0-221517K0101769/get_state
```

Set brightness (with arguments):
```bash
curl -X POST http://localhost:5000/device/uuid:Dimmer-1_0-221517K0101770/set_brightness \
  -H "Content-Type: application/json" \
  -d '{"args": [75]}'
```

## Supported Devices

This API works with any WeMo device supported by the pywemo library, including:

- **WeMo Switch** - Smart plugs and wall switches
- **WeMo Dimmer** - Dimmable light switches  
- **WeMo Light Switch** - Basic light switches
- **WeMo Motion** - Motion sensors
- **WeMo Maker** - DIY automation device
- **WeMo Insight Switch** - Smart plugs with energy monitoring
- **WeMo Bulbs** - Smart light bulbs

## Configuration

### Environment Variables

The application can be configured using environment variables:

- `FLASK_ENV`: Set to `development` for debug mode
- `PORT`: Change the default port (default: 5000)

### Network Requirements

- The API server must be on the same network as your WeMo devices
- WeMo devices use UPnP for discovery on port 1900
- Individual devices typically listen on port 49153

## Development

### Local Development

1. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run in development mode**:
   ```bash
   FLASK_ENV=development python app.py
   ```

### Docker Development

Build and run with Docker:
```bash
docker build -t pywemo-api .
docker run -p 5000:5000 pywemo-api
```

## Troubleshooting

### Device Discovery Issues

1. **Ensure devices are on the same network**: WeMo devices must be on the same subnet as the API server
2. **Check firewall settings**: Make sure UDP port 1900 (UPnP) is not blocked
3. **Manual discovery**: Use the `/device/discover_by_ip` endpoint if automatic discovery fails
4. **Refresh devices**: Call `/devices/refresh` if devices become unavailable

### Common Error Responses

- `404 Device not found`: The UDN doesn't match any discovered device
- `404 Method not found`: The requested method doesn't exist on the device
- `400 Bad Request`: Invalid arguments passed to device method

## Dependencies

- **Flask**: Web framework for the REST API
- **pywemo**: Python library for WeMo device control
- **Python 3.11+**: Recommended Python version

## Contributing

1. Fork the repository
2. Share your work with others

That's it. I have a day job so, realistically, I'm not going to be maintaining this except for my own usage.

## License

This project is open source and available under the [MIT License](LICENSE).

## Related Projects

- [pywemo](https://github.com/pywemo/pywemo) - The underlying Python library for WeMo control
- [Home Assistant WeMo Integration](https://www.home-assistant.io/integrations/wemo/) - WeMo integration for Home Assistant

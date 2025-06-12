# NetworkEyes Plugin

A BrainDrive plugin for real-time network status monitoring and connectivity checking.

## Overview

NetworkEyes provides network connectivity monitoring capabilities for BrainDrive services. It features a dashboard to track network status, connection health, service availability, and supports advanced configuration and installation options.

## Features

- **Real-time Monitoring**: Continuous network status updates
- **Service Health Checks**: Monitor BrainDrive service connectivity, including Ollama endpoints
- **Visual Dashboard**: Intuitive and clear network status indicators
- **Configurable Targets**: Easily add or modify services to monitor
- **Automatic Refresh**: Periodic status updates with configurable intervals
- **Detailed Statistics**: View network metrics and connection quality
- **Alert Notifications**: Optional alerts for service failures or degraded performance
- **Error Handling**: Robust timeout and retry support for network requests

## Installation

### From GitHub Releases (Recommended)

1. Go to the BrainDrive Plugin Manager
2. Click "Install Plugins"
3. Enter the repository URL: `https://github.com/DJJones66/NetworkEyes`
4. Click "Install Plugin"

### Manual Installation

1. Download the latest release from GitHub
2. Extract the plugin files
3. Use the BrainDrive plugin installer or follow these steps:

```bash
# Copy to user plugin directory
cp -r plugins/NetworkEyes /path/to/braindrive/plugins/<user_id>/networkeyes/
```

4. Run plugin initializer:

```python
from plugins.NetworkEyes.plugin_initializer import NetworkEyesInitializer

initializer = NetworkEyesInitializer()
await initializer.initialize(user_id, db_session)
```

### Prerequisites

- BrainDrive 1.0.0 or higher
- Node.js v18+
- Python 3.7+

## Configuration

### Plugin Settings

These can be configured via the plugin UI or a JSON file in the plugin data directory:

```json
{
  "monitoring_targets": [
    {
      "name": "Ollama",
      "url": "https://www.ollama.com",
      "enabled": true,
      "timeout": 3000
    },
    {
      "name": "Local Ollama",
      "url": "http://localhost:11434",
      "enabled": true,
      "timeout": 3000
    }
  ],
  "check_interval": 30000,
  "retry_attempts": 3,
  "notification_enabled": true
}
```

#### Supported Options

- **refresh_interval**: Auto-refresh interval in milliseconds (default: 30000)
- **show_details**: Toggle display of detailed stats (default: true)
- **timeout**: Request timeout in ms (default: 3000)

## Module: Network Status Monitor

### Description

Real-time dashboard for monitoring network connectivity and service health.

### Features

- Live network status indicators
- Connection quality and availability
- Historical data and alerts
- Visual feedback on status and latency

### Layout

- **Minimum Size**: 3x2 grid units
- **Default Size**: 4x3 grid units
- **Resizable**: Yes

## Development

### Project Structure

```
plugins/NetworkEyes/
├── src/
│   ├── ComponentNetworkStatus.tsx
│   ├── index.tsx
│   ├── bootstrap.tsx
│   └── styles/
├── scripts/
│   ├── install.py
│   ├── validate.py
│   └── build.sh
├── dist/
├── plugin_initializer.py
├── package.json
├── webpack.config.js
├── tsconfig.json
└── tailwind.config.js
```

### Building and Running

```bash
# Install dependencies
npm install

# Dev mode
npm run dev

# Production build
npm run build

# Validate
npm run validate
# or
python3 scripts/validate.py
```

### Validation Checklist

- ✅ Required files and structure
- ✅ Plugin initializer logic
- ✅ TypeScript compile check
- ✅ React component structure
- ✅ Build artifacts verified
- ✅ Network check functionality tested

## Plugin Architecture

### Initializer Pattern

This plugin uses BrainDrive’s initializer system for robust setup:

- Database registration
- Per-user plugin instance and directory setup
- Auto-cleanup on error
- Extensible with additional modules

### Key Components

- `plugin_initializer.py`: Registers plugin and modules, sets up environment
- `scripts/install.py`: Handles installation logic
- `scripts/validate.py`: Ensures build and setup correctness

## Permissions

- `network.read`: Read network status and perform health checks
- `storage.read`: Load plugin configuration and cached data
- `storage.write`: Save plugin settings and status history

## Technical Details

- **Bundle Method**: Webpack Module Federation
- **Entry Point**: `dist/remoteEntry.js`
- **Framework**: React 18+
- **Language**: TypeScript
- **Installation Type**: Remote or Manual

## Compatibility

- **BrainDrive Version**: 1.0.0+
- **Plugin API**: 1.0.0
- **Browser Support**: Modern browsers with ES2020+

## Troubleshooting

1. **Build Issues**  
   Try cleaning and rebuilding:
   ```bash
   rm -rf node_modules dist
   npm install
   npm run build
   ```

2. **Validation Errors**  
   Run:
   ```bash
   python3 scripts/validate.py
   ```

3. **Network Problems**  
   - Ensure services are running
   - Check firewall rules
   - Confirm CORS settings if using external URLs

4. **Debug Logging**
   ```python
   import logging
   logging.getLogger('plugins.NetworkEyes').setLevel(logging.DEBUG)
   ```

## Contributing

1. Fork the repo
2. Create a feature branch
3. Implement your feature or fix
4. Run validation
5. Submit a pull request

## Version History

### v1.0.0

- Initial release
- Core network monitoring functionality
- Ollama connectivity checks
- Plugin validation and installation logic

## Support

- **GitHub Issues**: [https://github.com/DJJones66/NetworkEyes/issues](https://github.com/DJJones66/NetworkEyes/issues)
- **Repository**: [https://github.com/DJJones66/NetworkEyes](https://github.com/DJJones66/NetworkEyes)

## License

MIT License – see LICENSE file for details.

# SF Transit Tracker 🚌🚊🚇

A real-time Bay Area transit monitoring system that tracks 1700+ vehicles across multiple transit agencies. Built with Flask and WebSocket technology, featuring an interactive map with smooth animations and dual theme support.

![Python](https://img.shields.io/badge/python-3.12-blue.svg)
![Flask](https://img.shields.io/badge/flask-2.3.3-green.svg)
![WebSocket](https://img.shields.io/badge/websocket-enabled-brightgreen.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## 🎯 Features

- **Real-time Vehicle Tracking**: Monitor 1700+ transit vehicles across the Bay Area
- **Multi-Agency Support**: 
  - SF Muni (buses, light rail, cable cars)
  - BART trains
  - Golden Gate Transit (buses and ferries)
  - AC Transit
  - Regional transit (entire Bay Area)
- **Dual Theme System**: Toggle between cyberpunk TRON theme and clean default theme
- **Smooth Animations**: Physics-based vehicle movement with 30 FPS throttling
- **WebSocket Updates**: Real-time data streaming with automatic HTTP fallback
- **Interactive Filters**: Show/hide specific transit types
- **Route Visualization**: Display GTFS route shapes on the map

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- pip package manager
- 511.org API key (optional but recommended)
- BART API key (optional)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/sf-transit-tracker.git
cd sf-transit-tracker
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env and add your API keys
```

5. Run the application:
```bash
python app.py
```

6. Open your browser to http://localhost:5001

## 🐳 Docker Production Testing

### CRITICAL: Always Test with Exact Production Configuration

When testing Docker locally, you MUST use the exact production command to catch configuration issues:

```bash
# Build the Docker image
docker build -t sf-transit-tracker .

# Run with EXACT production configuration
docker run -d -p 5002:8080 --name sf-transit-test --env-file .env sf-transit-tracker \
  gunicorn --bind 0.0.0.0:8080 --workers 2 \
  --worker-class gevent --worker-connections 1000 \
  --timeout 30 --keep-alive 2 --max-requests 1000 \
  --max-requests-jitter 100 --log-level info \
  --access-logfile - --error-logfile - app:app

# Check logs for any issues
docker logs -f sf-transit-test

# Test the application
curl http://localhost:5002/api/health
```

**Why This Matters:**
- Default Docker run uses single process (hides multi-worker issues)
- Production uses gevent workers (async mode must match)
- Multiple workers expose session management problems
- Catches Socket.IO configuration mismatches early

### Production Testing Checklist
- [ ] Monitor connection status (should show "Connected")
- [ ] Check logs for HTTP 400 errors
- [ ] Test with multiple browser tabs
- [ ] Verify connections survive for 5+ minutes
- [ ] Ensure worker recycling doesn't break sessions

## 🔧 Configuration

Create a `.env` file with the following variables:

```env
# API Keys (optional but recommended for better data)
SF_511_API_KEY=your_511_api_key_here
BART_API_KEY=your_bart_api_key_here

# Server Configuration
DEBUG=True
SECRET_KEY=your-secret-key-here
PORT=5001
```

## 📁 Project Structure

```
sf-transit-tracker/
├── app.py                      # Main Flask application (modular, ~100 lines)
├── requirements.txt            # Python dependencies
├── .env.example               # Environment variables template
├── CLAUDE.md                  # AI assistant instructions
├── backend/                   # Backend modules (NEW - modular architecture)
│   ├── models/
│   │   ├── vehicle.py        # Vehicle dataclass & models
│   │   └── gtfs.py          # GTFS data processing
│   ├── services/
│   │   ├── transit_fetcher.py    # API data fetching (511.org, BART)
│   │   └── background_updater.py # Background update cycles
│   └── api/
│       ├── routes.py        # Main API endpoints (/api/*)
│       ├── test_routes.py   # Test endpoints (/test/*)
│       └── websocket.py     # WebSocket handlers
├── static/                    # Frontend assets
│   ├── js/
│   │   └── TransitTracker.js    # Modular JavaScript class (NEW)
│   ├── themes/                  # Theme system (NEW)
│   │   ├── default/
│   │   │   └── default-theme.css  # Clean default styling
│   │   └── tron/                  # TRON theme (preserved for future)
│   │       ├── tron-theme.css
│   │       ├── tron-vehicles.css
│   │       └── tron-animations.css
│   └── routeManager.js          # GTFS route management
├── templates/                   # HTML templates
│   ├── index.html              # Original monolithic version
│   ├── index_clean.html        # NEW - Modular version (default route)
│   ├── test.html               # API testing dashboard
│   └── data_monitor.html       # Real-time data monitor
├── tests/                      # Test scripts
│   ├── enhanced_test_apis.py   # Comprehensive API tests
│   └── test_511.py             # 511.org connectivity test
├── docs/                       # Documentation
│   ├── REFACTORING_PLAN.md     # Detailed refactoring progress
│   └── TESTING_STRATEGY.md     # Testing approach
└── data/                       # GTFS data storage (auto-created)
```

## 🎨 Themes

The application supports two visual themes:

### Default Theme (Current)
- Clean, professional styling matching original implementation
- Standard OpenStreetMap tiles
- Rounded corners and soft shadows
- Optimized for readability and performance

### TRON Theme (Future Integration)
- Cyberpunk aesthetic with glowing effects
- Dark map tiles with neon accents  
- Animated grid background
- Sharp, futuristic UI elements
- **Status**: Preserved in `static/themes/tron/` for Phase 4 implementation

**Current Version**: The application currently uses the clean default theme. TRON theme integration is planned for a future phase.

## 🔌 API Endpoints

### HTTP Endpoints
- `GET /` - Main application interface (modular version)
- `GET /original` - Original monolithic version (for comparison)
- `GET /api/vehicles` - Current vehicle positions with individual timestamps
- `GET /api/routes` - GTFS route shapes
- `GET /api/refresh-routes` - Trigger GTFS data refresh
- `GET /api/health` - System health check
- `GET /test` - API testing dashboard
- `GET /data_monitor` - Real-time data monitoring

### WebSocket Events
- `connect` - Client connection established
- `request_update` - Client requests latest data
- `vehicle_update` - Server broadcasts vehicle positions

## 🧪 Testing

Run the comprehensive API test suite:

```bash
# Test all transit APIs with detailed route breakdown
python tests/enhanced_test_apis.py

# Test 511.org connectivity
python tests/test_511.py
```

Or use the web-based testing dashboard at http://localhost:5001/test

## 📊 Data Sources

- **511.org**: Primary source for SF Muni, Golden Gate Transit, AC Transit
  - **Individual Vehicle Timestamps**: Now extracts actual GTFS timestamp per vehicle (not bulk processing time)
  - **Route Information**: Uses vehicle label field for accurate route number display
  - **Regional Filtering**: Properly excludes duplicate Regional (RG) vehicles
- **BART API**: Real-time train positions (simulated from ETD data)
- **GTFS Static Data**: Route shapes from multiple sources with fallback chain

## 🆕 Recent Improvements (Phase 2 Refactoring)

### Architecture Enhancements
- **Modular Backend**: Split monolithic `app.py` (1500+ lines) into focused modules (~100 lines)
- **Organized Frontend**: Extracted JavaScript into maintainable `TransitTracker` class
- **Theme System**: Separated TRON and default themes for future customization
- **Port Change**: Moved to port 5001 to avoid macOS AirPlay conflicts

### Animation System
- **Physics-Based Movement**: Restored complete vehicle animation with speed/heading calculations
- **35-Second Interpolation**: Smooth movement between data updates with predictive positioning
- **Viewport Optimization**: Improved performance with smart bounds checking
- **Fade Effects**: New vehicles appear with smooth fade-in animation

### Data Quality
- **Individual Timestamps**: Vehicle popups show actual GTFS reporting times (not bulk fetch time)
- **Accurate Route Numbers**: Fixed empty route display using vehicle label data
- **Proper Vehicle Counting**: Eliminated duplicate regional vehicles for accurate filter counts
- **Enhanced Type Mapping**: Better distinction between transit agency vehicle types

## 🚀 Performance Optimizations

### Frontend
- Viewport culling - only animate visible vehicles
- 30 FPS animation throttling
- CSS variables for instant theme switching
- Efficient marker management with automatic cleanup

### Backend
- Connection pooling for API requests
- 30-second update cycles to balance freshness and load
- Graceful error handling with fallbacks
- Local GTFS data caching

## 🛠️ Development

### Adding New Transit Agencies

1. Add agency configuration to `AGENCIES` dict in `app.py`
2. Implement data fetching in `fetch_511_vehicles()` or create new fetcher
3. Add agency filter to `templates/index.html`
4. Update vehicle type mapping in `determine_vehicle_type()`

### Customizing Themes

Edit the CSS custom properties in `static/main.css`:

```css
[data-theme="tron"] {
  --primary-color: #00ffff;
  --background-color: #0a0a0a;
  /* ... more variables ... */
}
```

## 🐛 Troubleshooting

### No vehicles appearing
- Check API keys in `.env` file
- Verify internet connectivity
- Check browser console for WebSocket errors
- Use `/test` endpoint to debug API connections

### Performance issues
- Reduce number of active vehicle types using filters
- Check browser performance profiler
- Ensure 30 FPS throttling is working

### WebSocket connection failures
- Application automatically falls back to HTTP polling
- Check for firewall/proxy blocking WebSocket connections
- Verify Flask-SocketIO is properly installed

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 🙏 Acknowledgments

- [511.org](https://511.org) for Bay Area transit data
- [BART](https://www.bart.gov) for train tracking API
- [Leaflet](https://leafletjs.com) for mapping functionality
- [Flask-SocketIO](https://flask-socketio.readthedocs.io) for real-time capabilities

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Check existing issues for solutions
- Review the `/test` endpoint for API debugging

---

Built with ❤️ for Bay Area transit riders
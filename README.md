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

6. Open your browser to http://localhost:5000

## 🔧 Configuration

Create a `.env` file with the following variables:

```env
# API Keys (optional but recommended for better data)
SF_511_API_KEY=your_511_api_key_here
BART_API_KEY=your_bart_api_key_here

# Server Configuration
DEBUG=True
SECRET_KEY=your-secret-key-here
PORT=5000
```

## 📁 Project Structure

```
sf-transit-tracker/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── CLAUDE.md             # AI assistant instructions
├── static/               # Frontend assets
│   ├── main.css         # Core styles
│   ├── animations.css   # Animation definitions
│   ├── components.css   # UI component styles
│   ├── panels.css       # Control panel styles
│   ├── vehicles.css     # Vehicle marker styles
│   └── routeManager.js  # GTFS route management
├── templates/            # HTML templates
│   ├── index.html       # Main application
│   ├── test.html        # API testing dashboard
│   └── data_monitor.html # Real-time data monitor
├── tests/                # Test scripts
│   ├── enhanced_test_apis.py # Comprehensive API tests
│   ├── test_511.py          # 511.org connectivity test
│   └── nextmuni_api.py      # NextMuni API utilities
└── data/                 # GTFS data storage (auto-created)
```

## 🎨 Themes

The application supports two visual themes:

### TRON Theme (Default)
- Cyberpunk aesthetic with glowing effects
- Dark map tiles with neon accents
- Animated grid background
- Sharp, futuristic UI elements

### Default Theme
- Clean, professional styling
- Light map tiles
- Rounded corners and soft shadows
- Better for daytime viewing

Toggle themes using the button in the top-right corner.

## 🔌 API Endpoints

### HTTP Endpoints
- `GET /` - Main application interface
- `GET /api/vehicles` - Current vehicle positions
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

Or use the web-based testing dashboard at http://localhost:5000/test

## 📊 Data Sources

- **511.org**: Primary source for SF Muni, Golden Gate Transit, AC Transit
- **BART API**: Real-time train positions (simulated from ETD data)
- **GTFS Static Data**: Route shapes from multiple sources with fallback chain

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
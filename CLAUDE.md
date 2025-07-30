# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SF Transit Tracker is a real-time Bay Area transit monitoring system built with Flask and Socket.IO technology. It integrates multiple transit APIs (511.org, BART) to track 1,500+ vehicles across the entire Bay Area, displaying them on an interactive map with smooth animations, location-based auto-zoom, and dark theme support.

## Architecture

### Backend (Flask + WebSocket)
- **Main App**: `app.py` - Flask server with Flask-SocketIO for real-time communication
- **Data Sources**: 511.org GTFS-Realtime (SFMTA, Golden Gate, AC Transit), BART API
- **Background Processing**: 30-second update cycles with vehicle position interpolation
- **GTFS Integration**: Downloads and processes route shapes from multiple sources

### Frontend (Vanilla JS + Leaflet)
- **Core**: `TransitTracker` class handles map, vehicles, animations, location
- **Real-time**: Socket.IO HTTP polling for connection tracking
- **Animation System**: Physics-based vehicle movement with 30 FPS throttling
- **Location Services**: Geolocation API with smart auto-zoom to user's neighborhood
- **User Location**: "You are here" marker with configurable zoom levels
- **Theme System**: Dark mode with readable street names and labels

### Key Data Flow
1. Background thread fetches from APIs every 30s
2. Data normalized into Vehicle objects 
3. WebSocket broadcasts to connected clients
4. Frontend interpolates smooth movement between updates
5. Automatic cleanup of expired vehicles prevents memory leaks

## Common Commands

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
python app.py
# Main app: http://localhost:5000
# Test dashboard: http://localhost:5000/test
# Data monitor: http://localhost:5000/data_monitor
```

### Testing
```bash
# Comprehensive API testing with route breakdown
python tests/enhanced_test_apis.py

# Test 511.org connectivity
python tests/test_511.py

# Individual API testing via web dashboard
# Navigate to /test endpoint for interactive testing
```

### API Endpoints
- `GET /api/vehicles` - Current vehicle positions
- `GET /api/routes` - GTFS route shapes  
- `GET /api/refresh-routes` - Trigger GTFS data refresh
- `GET /api/health` - System status
- `WebSocket /` - Real-time vehicle updates

## Performance Considerations

### Frontend Optimizations
- **Animation Throttling**: 30 FPS cap prevents performance issues
- **Viewport Culling**: Only animates visible vehicles
- **Location Services**: Configurable timeout and caching for geolocation
- **CSS Variables**: Eliminates duplicate theme styles
- **Tile Layer Caching**: Instant theme switching
- **Memory Management**: Automatic cleanup of removed vehicles

### Backend Optimizations
- **Connection Pooling**: Reused HTTP sessions for API calls
- **Error Handling**: Graceful fallbacks for failed API requests
- **Data Caching**: GTFS route data cached locally
- **Efficient Updates**: Only broadcasts when vehicle data changes

## Key Files

- `app.py` - Main Flask application with all API integrations  
- `templates/index_clean.html` - Primary web interface with map and controls (production)
- `templates/index.html` - Legacy monolithic template (available at /original)
- `static/js/TransitTracker.js` - Main application class with location services
- `static/routeManager.js` - GTFS route data management
- `static/themes/default/default-theme.css` - Modular theme and component styles
- `tests/enhanced_test_apis.py` - Comprehensive API testing script
- `templates/test.html` - Interactive API testing dashboard

## Vehicle Data Model

Each vehicle object contains:
- `id`, `agency`, `type` (muni-bus, bart-train, ferry, etc.)
- `lat`, `lng`, `speed`, `heading` for positioning
- `route`, `destination` for display
- `last_update` timestamp for data freshness

## Theme System

The application supports two themes controlled via CSS custom properties:
- **TRON Theme**: Cyberpunk aesthetic with glowing effects, sharp edges, animated grid
- **Default Theme**: Clean, professional styling with rounded corners
- Switch via theme toggle button (top-right) - changes tiles, colors, animations instantly

## Testing Infrastructure

The project includes comprehensive testing tools:
- Web-based testing dashboard at `/test` endpoint
- Command-line scripts for API validation
- Real-time monitoring interface at `/data_monitor`
- Route-level analysis and breakdown tools

## Data Sources

- **511.org**: Primary GTFS-Realtime source for SF, Golden Gate, AC Transit
- **BART API**: Direct integration for train positions (simulated from ETD data)
- **GTFS Static**: Route shapes from Transit.land, SFMTA, 511.org (fallback chain)

## Development Notes

- Frontend uses vanilla JavaScript (no build system required)
- Real-time updates via Socket.IO HTTP polling (NOT WebSockets)
- Vehicle animations use physics-based interpolation for smooth movement
- Location-based auto-zoom detects user's location and centers map
- All API calls include proper error handling and retry logic
- Theme switching preserves all vehicle states and positions

## CRITICAL: Docker Production Testing

**ALWAYS test Docker with the EXACT production command:**

```bash
docker run -d -p 5002:8080 --name sf-transit-test --env-file .env sf-transit-tracker \
  gunicorn --bind 0.0.0.0:8080 --workers 2 \
  --worker-class gevent --worker-connections 1000 \
  --timeout 30 --keep-alive 2 --max-requests 1000 \
  --max-requests-jitter 100 --log-level info \
  --access-logfile - --error-logfile - app:app
```

**Never use simplified Docker run** - it hides critical issues like:
- Socket.IO async mode mismatches (gevent vs threading)
- Multi-worker session management problems
- Worker recycling breaking connections
- HTTP 400 errors from configuration conflicts

**Production Testing Must-Dos:**
- Check Socket.IO shows "Connected" (not "Disconnected")
- Monitor logs for HTTP 400 errors
- Test with multiple concurrent connections
- Verify sessions survive worker recycling
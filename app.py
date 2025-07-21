#!/usr/bin/env python3
"""
SF Transit Tracker - Python Flask Server
Real-time San Francisco transit data fetcher and WebSocket server
"""

import os
import json
import time
import threading
import requests
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict
import logging
import zipfile
import csv
from io import StringIO, BytesIO

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from dotenv import load_dotenv

# Import models and services
from backend.models.vehicle import Vehicle
from backend.models.gtfs import GTFSProcessor
from backend.services.transit_fetcher import TransitDataFetcher

# GTFS Realtime imports
try:
    from google.transit import gtfs_realtime_pb2
except ImportError:
    print("Installing gtfs-realtime-bindings...")
    os.system("pip install gtfs-realtime-bindings")
    from google.transit import gtfs_realtime_pb2

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app configuration
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'sf-transit-secret-key')
app.config['DEBUG'] = os.getenv('DEBUG', 'True').lower() == 'true'

# Enable CORS and SocketIO
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# API Configuration
API_KEYS = {
    'SF_511': os.getenv('SF_511_API_KEY', 'YOUR_511_API_KEY'),
    'BART': os.getenv('BART_API_KEY', 'YOUR_BART_API_KEY')
}





# Global data fetcher instance
data_fetcher = TransitDataFetcher(API_KEYS)



# Initialize GTFS processor
gtfs_processor = GTFSProcessor()


def background_data_update():
    """Background thread to fetch data every 30 seconds"""
    while True:
        try:
            logger.info("Fetching transit data...")
            start_time = time.time()

            vehicles = data_fetcher.fetch_all_data()

            fetch_time = (time.time() - start_time) * 1000  # Convert to milliseconds

            # Emit to all connected clients
            socketio.emit('bulk_update', {
                'vehicles': [vehicle.to_dict() for vehicle in vehicles.values()],
                'timestamp': data_fetcher.last_update.isoformat(),
                'fetchTime': fetch_time,
                'count': len(vehicles)
            })

            logger.info(f"Updated {len(vehicles)} vehicles in {fetch_time:.0f}ms")

        except Exception as e:
            logger.error(f"Error in background update: {e}")
            socketio.emit('error', {
                'message': f'Data fetch error: {str(e)}',
                'timestamp': datetime.now().isoformat()
            })

        time.sleep(30)  # Wait 30 seconds


# Helper functions for enhanced analysis
def _extract_direction_from_vehicle(vehicle):
    """Extract direction/destination from GTFS vehicle data"""
    direction = ""

    # Try trip headsign first
    if vehicle.HasField('trip'):
        if hasattr(vehicle.trip, 'trip_headsign'):
            direction = vehicle.trip.trip_headsign
        elif hasattr(vehicle.trip, 'direction_id'):
            direction = "Inbound" if vehicle.trip.direction_id == 0 else "Outbound"

    # Fallback to compass heading
    if not direction and vehicle.HasField('position') and vehicle.position.HasField('bearing'):
        bearing = vehicle.position.bearing
        if 315 <= bearing < 45:
            direction = "Northbound"
        elif 45 <= bearing < 135:
            direction = "Eastbound"
        elif 135 <= bearing < 225:
            direction = "Southbound"
        elif 225 <= bearing < 315:
            direction = "Westbound"

    return direction


def _get_transport_type_name(vehicle_type):
    """Get friendly name for transport type"""
    names = {
        'muni-bus': 'Muni Buses',
        'light-rail': 'Light Rail Lines',
        'cable-car': 'Cable Car Lines',
        'bart-train': 'BART Trains',
        'ferry': 'Ferry Routes',
        'bus': 'Bus Routes'
    }
    return names.get(vehicle_type, vehicle_type.title())


# Flask routes
@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')


@app.route('/test')
def test_page():
    """Serve the API test dashboard"""
    return render_template('test.html')


@app.route('/data_monitor')
def data_monitor_page():
    """Serve the API test dashboard"""
    return render_template('data_monitor.html')


# REST API endpoints
@app.route('/api/vehicles')
def get_vehicles():
    """REST endpoint for vehicle data"""
    vehicles_dict = {vid: vehicle.to_dict() for vid, vehicle in data_fetcher.vehicles.items()}
    return jsonify({
        'vehicles': list(vehicles_dict.values()),
        'lastUpdate': data_fetcher.last_update.isoformat() if data_fetcher.last_update else None,
        'count': len(vehicles_dict)
    })


@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'vehicles': len(data_fetcher.vehicles),
        'lastUpdate': data_fetcher.last_update.isoformat() if data_fetcher.last_update else None,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/routes')
def get_routes():
    """Serve route shape data for transit lines - Now using real GTFS data"""

    # Try to load from file first
    route_data = gtfs_processor.load_route_shapes()

    if route_data and 'routes' in route_data:
        # Real GTFS data available
        return jsonify({
            'routes': route_data['routes'],
            'metadata': route_data.get('metadata', {})
        })
    else:
        # Fallback to hand-coded data if no GTFS data available
        logger.warning("No GTFS route data found, using fallback hand-coded routes")

        # Hand-coded key waypoints for Muni Light Rail lines (fallback)
        routes = {
            'J': {
                'name': 'J-Church',
                'agency': 'SFMTA',
                'type': 'light-rail',
                'shape': [
                    [37.7928, -122.3968],  # Embarcadero Station
                    [37.7894, -122.4014],  # Montgomery
                    [37.7844, -122.4079],  # Powell
                    [37.7795, -122.4136],  # Civic Center
                    [37.7762, -122.4181],  # Van Ness
                    [37.7735, -122.4210],  # 16th & Mission
                    [37.7678, -122.4202],  # 24th & Mission
                    [37.7594, -122.4267],  # Glen Park
                    [37.7520, -122.4320],  # Diamond Heights
                    [37.7449, -122.4370],  # Clipper
                    [37.7381, -122.4419],  # Church & 30th
                    [37.7334, -122.4469]  # Balboa Park
                ]
            },
            'N': {
                'name': 'N-Judah',
                'agency': 'SFMTA',
                'type': 'light-rail',
                'shape': [
                    [37.7928, -122.3968],  # Embarcadero Station
                    [37.7894, -122.4014],  # Montgomery
                    [37.7844, -122.4079],  # Powell
                    [37.7795, -122.4136],  # Civic Center
                    [37.7762, -122.4181],  # Van Ness
                    [37.7660, -122.4467],  # Duboce & Church
                    [37.7654, -122.4539],  # Carl & Cole
                    [37.7654, -122.4634],  # Carl & Stanyan
                    [37.7654, -122.4728],  # 9th & Irving
                    [37.7654, -122.4825],  # 19th & Irving
                    [37.7654, -122.4959],  # 28th & Irving
                    [37.7654, -122.5093]  # Ocean Beach
                ]
            }
        }

        return jsonify({
            'routes': routes,
            'metadata': {
                'phase': 'fallback',
                'type': 'hand-coded-waypoints',
                'count': len(routes),
                'lastUpdated': datetime.now().isoformat()
            }
        })


@app.route('/api/refresh-routes')
def refresh_routes():
    """Manually refresh GTFS route data"""
    try:
        logger.info("Starting GTFS route refresh...")

        # Check if we have API key
        if API_KEYS['SF_511'] == 'YOUR_511_API_KEY':
            return jsonify({
                'status': 'error',
                'message': 'SF_511_API_KEY not configured'
            }), 400

        # Download GTFS data
        gtfs_data = gtfs_processor.download_sfmta_gtfs(API_KEYS['SF_511'])

        if not gtfs_data:
            return jsonify({
                'status': 'error',
                'message': 'Failed to download GTFS data'
            }), 500

        # Parse shapes for J and N routes
        route_shapes = gtfs_processor.parse_shapes_for_routes(gtfs_data, ['J', 'N'])

        if not route_shapes:
            return jsonify({
                'status': 'error',
                'message': 'No route shapes found for J and N lines'
            }), 404

        # Save to file
        success = gtfs_processor.save_route_shapes(route_shapes)

        if success:
            # Get summary statistics
            stats = {}
            for route_key, route_data in route_shapes.items():
                stats[route_key] = len(route_data['shape'])

            return jsonify({
                'status': 'success',
                'message': f'Successfully updated {len(route_shapes)} route shapes',
                'routes_updated': list(route_shapes.keys()),
                'point_counts': stats,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to save route shapes'
            }), 500

    except Exception as e:
        logger.error(f"Error refreshing routes: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# API Testing Endpoints
@app.route('/test/511-api')
def test_511_api():
    """Test 511.org API connectivity with optional agency filter"""
    try:
        if API_KEYS['SF_511'] == 'YOUR_511_API_KEY':
            return jsonify({
                'error': 'API key not configured',
                'apiKeyValid': False,
                'message': 'Please set SF_511_API_KEY in .env file'
            }), 400

        # Get agency filter from query parameter
        agency_filter = request.args.get('agency', None)
        agencies_to_test = [agency_filter] if agency_filter else ['SF', 'GG', 'AC', 'RG']

        # Test the API call
        start_time = time.time()
        all_vehicles = []

        for agency in agencies_to_test:
            try:
                url = "http://api.511.org/transit/vehiclepositions"
                params = {
                    'api_key': API_KEYS['SF_511'],
                    'agency': agency
                }

                response = data_fetcher.session.get(url, params=params, timeout=15)
                if response.status_code == 200:
                    # Parse GTFS-Realtime data
                    feed = gtfs_realtime_pb2.FeedMessage()
                    feed.ParseFromString(response.content)

                    for entity in feed.entity:
                        if entity.HasField('vehicle') and entity.vehicle.HasField('position'):
                            vehicle = data_fetcher._parse_gtfs_vehicle(entity.vehicle, agency)
                            if vehicle:
                                all_vehicles.append(vehicle)
            except Exception as e:
                logger.error(f"Error testing {agency}: {e}")
                continue

        response_time = (time.time() - start_time) * 1000

        agencies = set()
        for vehicle in all_vehicles:
            if hasattr(vehicle, 'agency'):
                agencies.add(vehicle.agency)

        return jsonify({
            'apiKeyValid': True,
            'vehicleCount': len(all_vehicles),
            'agencies': list(agencies),
            'responseTime': response_time,
            'sampleVehicle': all_vehicles[0].to_dict() if all_vehicles else None,
            'testedAgency': agency_filter or 'ALL'
        })

    except Exception as e:
        return jsonify({
            'error': str(e),
            'apiKeyValid': False,
            'vehicleCount': 0
        }), 500


@app.route('/test/bart-overview')
def test_bart_overview():
    """BART lines overview - similar to analyze_bart_lines() from enhanced_test_apis.py"""
    try:
        if API_KEYS['BART'] == 'YOUR_BART_API_KEY':
            return jsonify({
                'error': 'BART API key not configured',
                'message': 'Please set BART_API_KEY in .env file'
            }), 400

        start_time = time.time()
        url = "https://api.bart.gov/api/etd.aspx"
        params = {
            'cmd': 'etd',
            'orig': 'ALL',
            'key': API_KEYS['BART'],
            'json': 'y'
        }

        response = data_fetcher.session.get(url, params=params, timeout=10)
        response_time = (time.time() - start_time) * 1000

        if response.status_code == 200:
            etd_data = response.json()
            lines = defaultdict(lambda: {'stations': set(), 'trains': 0, 'destinations': set()})

            if 'root' in etd_data and 'station' in etd_data['root']:
                stations = etd_data['root']['station']
                if not isinstance(stations, list):
                    stations = [stations]

                for station in stations:
                    station_name = station.get('name', 'Unknown')
                    if 'etd' in station:
                        etds = station['etd']
                        if not isinstance(etds, list):
                            etds = [etds]

                        for etd in etds:
                            destination = etd.get('destination', 'Unknown')
                            abbreviation = etd.get('abbreviation', destination[:4])

                            if 'estimate' in etd:
                                estimates = etd['estimate']
                                if not isinstance(estimates, list):
                                    estimates = [estimates]

                                train_count = len([e for e in estimates if e.get('minutes') != 'Leaving'])
                                lines[abbreviation]['stations'].add(station_name)
                                lines[abbreviation]['trains'] += train_count
                                lines[abbreviation]['destinations'].add(destination)

            # Format lines data
            formatted_lines = []
            total_trains = 0
            for line_code, data in sorted(lines.items()):
                destinations = list(data['destinations'])
                direction_text = f"{destinations[0]} ↔ {destinations[1]}" if len(
                    destinations) >= 2 else f"→ {destinations[0]}" if destinations else "Direction unknown"

                formatted_lines.append({
                    'code': line_code,
                    'trains': data['trains'],
                    'stations': len(data['stations']),
                    'direction': direction_text,
                    'destinations': destinations
                })
                total_trains += data['trains']

            return jsonify({
                'totalLines': len(formatted_lines),
                'totalTrains': total_trains,
                'totalStations': len(set().union(*[line['stations'] for line in lines.values()])),
                'responseTime': response_time,
                'lines': formatted_lines
            })

        else:
            return jsonify({
                'error': f'HTTP {response.status_code}'
            }), 500

    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500


@app.route('/test/bart-api')
def test_bart_api():
    """Test BART API connectivity"""
    try:
        if API_KEYS['BART'] == 'YOUR_BART_API_KEY':
            return jsonify({
                'error': 'API key not configured',
                'apiKeyValid': False,
                'message': 'Please set BART_API_KEY in .env file'
            }), 400

        start_time = time.time()
        vehicles = data_fetcher.fetch_bart_data(API_KEYS['BART'])
        response_time = (time.time() - start_time) * 1000

        return jsonify({
            'apiKeyValid': True,
            'trainCount': len(vehicles),
            'stationCount': len(set(v.id.split('-')[1] for v in vehicles if '-' in v.id)),
            'responseTime': response_time,
            'sampleTrain': vehicles[0].to_dict() if vehicles else None
        })

    except Exception as e:
        return jsonify({
            'error': str(e),
            'apiKeyValid': False,
            'trainCount': 0
        }), 500


# NextMuni API test endpoint removed - no longer needed as 511.org provides comprehensive SFMTA data


# Enhanced API Testing Endpoints
@app.route('/test/enhanced-511-api')
def test_enhanced_511_api():
    """Enhanced 511.org API analysis with route-level breakdown"""
    try:
        if API_KEYS['SF_511'] == 'YOUR_511_API_KEY':
            return jsonify({
                'error': 'API key not configured',
                'message': 'Please set SF_511_API_KEY in .env file'
            }), 400

        agencies = ['SF', 'GG', 'AC', 'RG']
        agency_results = {}
        total_vehicles = 0
        total_routes = 0

        for agency_code in agencies:
            try:
                start_time = time.time()
                url = "http://api.511.org/transit/vehiclepositions"
                params = {
                    'api_key': API_KEYS['SF_511'],
                    'agency': agency_code
                }

                response = data_fetcher.session.get(url, params=params, timeout=15)
                response_time = (time.time() - start_time) * 1000

                if response.status_code == 200:
                    # Parse GTFS-Realtime data
                    feed = gtfs_realtime_pb2.FeedMessage()
                    feed.ParseFromString(response.content)

                    # Group vehicles by route and transport type
                    routes = defaultdict(lambda: {'count': 0, 'vehicles': [], 'destinations': set(), 'type': ''})
                    transport_types = defaultdict(list)

                    for entity in feed.entity:
                        if entity.HasField('vehicle') and entity.vehicle.HasField('position'):
                            vehicle = entity.vehicle
                            route_id = vehicle.trip.route_id if vehicle.HasField('trip') else 'Unknown'

                            if not route_id or route_id in ['Unknown', '', None]:
                                continue

                            # Determine vehicle type
                            vehicle_type = data_fetcher._get_vehicle_type(route_id, agency_code)

                            # Extract destination/direction
                            destination = _extract_direction_from_vehicle(vehicle)

                            routes[route_id]['count'] += 1
                            routes[route_id]['type'] = vehicle_type
                            routes[route_id]['vehicles'].append({
                                'id': vehicle.vehicle.id,
                                'lat': vehicle.position.latitude,
                                'lng': vehicle.position.longitude,
                                'speed': vehicle.position.speed * 2.237 if vehicle.position.HasField('speed') else 0,
                                # m/s to mph
                                'heading': vehicle.position.bearing if vehicle.position.HasField('bearing') else 0
                            })
                            if destination:
                                routes[route_id]['destinations'].add(destination)

                    # Group by transport type and get top 5 routes per type
                    for route_id, data in routes.items():
                        transport_types[data['type']].append((route_id, data))

                    # Sort and limit to top 5 per transport type
                    transport_breakdown = {}
                    agency_vehicles = 0
                    agency_routes = 0

                    for transport_type, type_routes in transport_types.items():
                        sorted_routes = sorted(type_routes, key=lambda x: x[1]['count'], reverse=True)[:5]  # Top 5

                        type_info = {
                            'name': _get_transport_type_name(transport_type),
                            'routes': []
                        }

                        for route_id, route_data in sorted_routes:
                            destinations = list(route_data['destinations']) if route_data['destinations'] else []
                            type_info['routes'].append({
                                'route': route_id,
                                'count': route_data['count'],
                                'destinations': destinations[:2],  # Top 2 destinations
                                'sampleVehicle': route_data['vehicles'][0] if route_data['vehicles'] else None
                            })
                            agency_vehicles += route_data['count']
                            agency_routes += 1

                        transport_breakdown[transport_type] = type_info

                    agency_results[agency_code] = {
                        'name': data_fetcher._get_agency_name(agency_code),
                        'vehicleCount': agency_vehicles,
                        'routeCount': agency_routes,
                        'responseTime': response_time,
                        'transportTypes': transport_breakdown,
                        'status': 'success'
                    }

                    total_vehicles += agency_vehicles
                    total_routes += agency_routes

                else:
                    agency_results[agency_code] = {
                        'name': data_fetcher._get_agency_name(agency_code),
                        'error': f'HTTP {response.status_code}',
                        'status': 'error'
                    }

            except Exception as e:
                agency_results[agency_code] = {
                    'name': data_fetcher._get_agency_name(agency_code),
                    'error': str(e),
                    'status': 'error'
                }

        return jsonify({
            'totalVehicles': total_vehicles,
            'totalRoutes': total_routes,
            'agencies': agency_results,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({
            'error': str(e),
            'totalVehicles': 0
        }), 500


@app.route('/test/route-details/<agency>/<route>')
def test_route_details(agency, route):
    """Get detailed information for a specific route"""
    try:
        if API_KEYS['SF_511'] == 'YOUR_511_API_KEY':
            return jsonify({
                'error': 'API key not configured'
            }), 400

        start_time = time.time()
        url = "http://api.511.org/transit/vehiclepositions"
        params = {
            'api_key': API_KEYS['SF_511'],
            'agency': agency
        }

        response = data_fetcher.session.get(url, params=params, timeout=15)
        response_time = (time.time() - start_time) * 1000

        if response.status_code == 200:
            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(response.content)

            route_vehicles = []
            directions = defaultdict(int)

            for entity in feed.entity:
                if entity.HasField('vehicle') and entity.vehicle.HasField('position'):
                    vehicle = entity.vehicle
                    route_id = vehicle.trip.route_id if vehicle.HasField('trip') else 'Unknown'

                    if route_id == route:
                        direction = _extract_direction_from_vehicle(vehicle)
                        if direction:
                            directions[direction] += 1

                        route_vehicles.append({
                            'id': vehicle.vehicle.id,
                            'lat': vehicle.position.latitude,
                            'lng': vehicle.position.longitude,
                            'speed': vehicle.position.speed * 2.237 if vehicle.position.HasField('speed') else 0,
                            'heading': vehicle.position.bearing if vehicle.position.HasField('bearing') else 0,
                            'direction': direction or 'Unknown'
                        })

            return jsonify({
                'agency': data_fetcher._get_agency_name(agency),
                'route': route,
                'vehicleCount': len(route_vehicles),
                'responseTime': response_time,
                'directions': dict(directions),
                'vehicles': route_vehicles[:10],  # Limit to 10 vehicles for display
                'vehicleType': data_fetcher._get_vehicle_type(route, agency)
            })

        else:
            return jsonify({
                'error': f'HTTP {response.status_code}'
            }), 500

    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500


@app.route('/test/bart-line-details/<line>')
def test_bart_line_details(line):
    """Get detailed BART line analysis"""
    try:
        if API_KEYS['BART'] == 'YOUR_BART_API_KEY':
            return jsonify({
                'error': 'BART API key not configured'
            }), 400

        start_time = time.time()
        url = "https://api.bart.gov/api/etd.aspx"
        params = {
            'cmd': 'etd',
            'orig': 'ALL',
            'key': API_KEYS['BART'],
            'json': 'y'
        }

        response = data_fetcher.session.get(url, params=params, timeout=10)
        response_time = (time.time() - start_time) * 1000

        if response.status_code == 200:
            etd_data = response.json()

            line_info = {
                'stations': set(),
                'departures': [],
                'directions': defaultdict(int),
                'nextTrains': []
            }

            if 'root' in etd_data and 'station' in etd_data['root']:
                stations = etd_data['root']['station']
                if not isinstance(stations, list):
                    stations = [stations]

                for station in stations:
                    station_name = station.get('name', 'Unknown')
                    station_abbr = station.get('abbr', 'UNK')

                    if 'etd' in station:
                        etds = station['etd']
                        if not isinstance(etds, list):
                            etds = [etds]

                        for etd in etds:
                            destination = etd.get('destination', 'Unknown')
                            abbreviation = etd.get('abbreviation', destination[:4])

                            # Check if this matches our line
                            if abbreviation.upper() == line.upper() or destination.replace(' ',
                                                                                           '').upper() == line.upper():
                                line_info['stations'].add(f"{station_name} ({station_abbr})")
                                line_info['directions'][destination] += 1

                                if 'estimate' in etd:
                                    estimates = etd['estimate']
                                    if not isinstance(estimates, list):
                                        estimates = [estimates]

                                    for estimate in estimates:
                                        minutes = estimate.get('minutes', 'Leaving')
                                        platform = estimate.get('platform', '?')

                                        line_info['departures'].append({
                                            'station': station_name,
                                            'destination': destination,
                                            'minutes': minutes,
                                            'platform': platform
                                        })

            # Sort departures by time
            def sort_key(x):
                if x['minutes'] == 'Leaving':
                    return 0
                elif str(x['minutes']).isdigit():
                    return int(x['minutes'])
                else:
                    return 999

            sorted_departures = sorted(line_info['departures'], key=sort_key)

            return jsonify({
                'line': line.upper(),
                'stationCount': len(line_info['stations']),
                'stations': sorted(list(line_info['stations'])),
                'trainCount': len(line_info['departures']),
                'directions': dict(line_info['directions']),
                'nextDepartures': sorted_departures[:10],  # Next 10 departures
                'responseTime': response_time
            })

        else:
            return jsonify({
                'error': f'HTTP {response.status_code}'
            }), 500

    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500


# Test GTFS connectivity
@app.route('/test/gtfs-connectivity')
def test_gtfs_connectivity():
    """Test connectivity to various GTFS sources"""
    try:
        if API_KEYS['SF_511'] == 'YOUR_511_API_KEY':
            return jsonify({
                'error': 'SF_511_API_KEY not configured',
                'message': 'Please set SF_511_API_KEY in .env file'
            }), 400

        # Test different GTFS sources
        test_results = {}

        sources = [
            ('511.org API', f'https://api.511.org/transit/datafeeds?api_key={API_KEYS["SF_511"]}&operator_id=SF'),
            ('Transit.land', 'https://transitland-atlas.s3.amazonaws.com/feeds/f-9q8y-sfmta.zip'),
            ('SFMTA Direct (HTTP)', 'http://gtfs.sfmta.com/transitdata/google_transit.zip'),
            ('511.org Status', 'https://api.511.org/transit/datafeeds')
        ]

        for name, url in sources:
            try:
                import time
                start_time = time.time()

                # Use GET for 511.org APIs, HEAD for others
                if '511.org' in url and 'datafeeds' in url:
                    # For 511.org datafeeds API, use GET but limit content reading
                    response = requests.get(url, timeout=15, allow_redirects=True, stream=True)

                    # Read just a small chunk to verify it's working
                    content_sample = b''
                    chunk_count = 0
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            content_sample += chunk
                            chunk_count += 1
                            if chunk_count >= 5:  # Read first 5KB only
                                break

                    # Check if it looks like ZIP content
                    is_zip = content_sample.startswith(b'PK')
                    content_type = 'application/zip' if is_zip else 'unknown'
                    content_length = f"~{len(content_sample)}+ bytes (sampled)"

                else:
                    # For other sources, use HEAD request
                    response = requests.head(url, timeout=15, allow_redirects=True)
                    content_type = response.headers.get('content-type', 'unknown')
                    content_length = response.headers.get('content-length', 'unknown')

                response_time = (time.time() - start_time) * 1000

                test_results[name] = {
                    'status': response.status_code,
                    'response_time': f"{response_time:.0f}ms",
                    'success': response.status_code in [200, 302],
                    'url': url,
                    'content_type': content_type,
                    'content_length': content_length
                }

                # Add extra info for 511.org API
                if name == '511.org API' and response.status_code == 200:
                    test_results[name]['is_zip_file'] = is_zip
                    test_results[name][
                        'sample_content'] = f"First bytes: {content_sample[:20].hex()}" if content_sample else "No content"

            except requests.exceptions.Timeout:
                test_results[name] = {
                    'status': 'TIMEOUT',
                    'error': 'Connection timeout (15s)',
                    'success': False,
                    'url': url
                }
            except requests.exceptions.ConnectionError as e:
                test_results[name] = {
                    'status': 'CONNECTION_ERROR',
                    'error': str(e),
                    'success': False,
                    'url': url
                }
            except Exception as e:
                test_results[name] = {
                    'status': 'ERROR',
                    'error': str(e),
                    'success': False,
                    'url': url
                }

        # Network diagnostics
        import socket
        try:
            # Test DNS resolution
            ip = socket.gethostbyname('gtfs.sfmta.com')
            dns_success = True
            dns_ip = ip
        except Exception as e:
            dns_success = False
            dns_ip = f"DNS Error: {e}"

        return jsonify({
            'connectivity_tests': test_results,
            'dns_resolution': {
                'hostname': 'gtfs.sfmta.com',
                'ip_address': dns_ip,
                'success': dns_success
            },
            'recommendations': generate_gtfs_recommendations(test_results),
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({
            'error': str(e),
            'message': 'GTFS connectivity test failed'
        }), 500


def generate_gtfs_recommendations(test_results):
    """Generate recommendations based on connectivity test results"""
    recommendations = []

    if not test_results.get('SFMTA Direct', {}).get('success'):
        recommendations.append("🚫 SFMTA Direct server appears to be down or unreachable")
        recommendations.append("💡 Try using the 511.org mirror as alternative")

    if not test_results.get('511.org Mirror', {}).get('success'):
        recommendations.append("🔑 Check your SF_511_API_KEY is valid")
        recommendations.append("🌐 Verify 511.org API access")

    if not test_results.get('DNS Test', {}).get('success'):
        recommendations.append("🌐 DNS resolution issues - check your internet connection")
        recommendations.append("🔥 Try using a different DNS server (8.8.8.8)")

    success_count = sum(1 for result in test_results.values() if result.get('success'))
    if success_count == 0:
        recommendations.append("❌ All GTFS sources failed - check firewall/network settings")
        recommendations.append("🏢 If on corporate network, HTTPS outbound may be blocked")

    if not recommendations:
        recommendations.append("✅ All connectivity tests passed - GTFS download should work")

    return recommendations

# SocketIO events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f"Client connected: {request.sid}")

    # Send current data to new client
    if data_fetcher.vehicles:
        emit('bulk_update', {
            'vehicles': [vehicle.to_dict() for vehicle in data_fetcher.vehicles.values()],
            'timestamp': data_fetcher.last_update.isoformat(),
            'count': len(data_fetcher.vehicles)
        })


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {request.sid}")


if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    import os

    if not os.path.exists('templates'):
        os.makedirs('templates')

    # Start background data fetching thread
    data_thread = threading.Thread(target=background_data_update, daemon=True)
    data_thread.start()

    # Get initial data
    data_fetcher.fetch_all_data()

    logger.info("Starting SF Transit Tracker server...")
    logger.info("Make sure to set your API keys in .env file:")
    logger.info("- SF_511_API_KEY")
    logger.info("- BART_API_KEY")

    # Run the Flask-SocketIO server
    socketio.run(
        app,
        host='127.0.0.1',
        port=5000,
        debug=True,
        use_reloader=False,  # Disable reloader to prevent double thread creation
        allow_unsafe_werkzeug=True  # Allow for development on Mac
    )
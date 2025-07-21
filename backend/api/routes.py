#!/usr/bin/env python3
"""
Main API routes for SF Transit Tracker
Contains core endpoints for vehicle data, health checks, and GTFS routes
"""

from flask import Blueprint, jsonify
from datetime import datetime
import logging

# Import the global instances (will be injected by main app)
data_fetcher = None
gtfs_processor = None

logger = logging.getLogger(__name__)

# Create Blueprint for main API routes
api_bp = Blueprint('api', __name__, url_prefix='/api')


def init_api_routes(df, gp):
    """Initialize API routes with global instances"""
    global data_fetcher, gtfs_processor
    data_fetcher = df
    gtfs_processor = gp


@api_bp.route('/vehicles')
def get_vehicles():
    """REST endpoint for vehicle data"""
    vehicles_dict = {vid: vehicle.to_dict() for vid, vehicle in data_fetcher.vehicles.items()}
    return jsonify({
        'vehicles': list(vehicles_dict.values()),
        'lastUpdate': data_fetcher.last_update.isoformat() if data_fetcher.last_update else None,
        'count': len(vehicles_dict)
    })


@api_bp.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'vehicles': len(data_fetcher.vehicles),
        'lastUpdate': data_fetcher.last_update.isoformat() if data_fetcher.last_update else None,
        'timestamp': datetime.now().isoformat()
    })


@api_bp.route('/routes')
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


@api_bp.route('/refresh-routes')
def refresh_routes():
    """Manually refresh GTFS route data"""
    try:
        logger.info("Starting GTFS route refresh...")

        # Check if we have API key - this will need to be passed in somehow
        # For now, we'll access it from the app context
        from flask import current_app
        api_keys = current_app.config.get('API_KEYS', {})
        
        if api_keys.get('SF_511') == 'YOUR_511_API_KEY':
            return jsonify({
                'status': 'error',
                'message': 'SF_511_API_KEY not configured'
            }), 400

        # Download GTFS data
        gtfs_data = gtfs_processor.download_sfmta_gtfs(api_keys['SF_511'])

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
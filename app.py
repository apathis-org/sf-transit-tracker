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
from backend.services.background_updater import BackgroundUpdater
from backend.api.routes import api_bp, init_api_routes
from backend.api.test_routes import test_bp, init_test_routes
from backend.api.websocket import init_websocket_handlers

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

# Store API keys in app config for blueprints
app.config['API_KEYS'] = API_KEYS





# Global instances
data_fetcher = TransitDataFetcher(API_KEYS)
gtfs_processor = GTFSProcessor()
background_updater = BackgroundUpdater(data_fetcher, socketio)

# Initialize API routes and WebSocket handlers with global instances
init_api_routes(data_fetcher, gtfs_processor)
init_test_routes(data_fetcher, API_KEYS)
init_websocket_handlers(data_fetcher, socketio)

# Register API blueprints
app.register_blueprint(api_bp)
app.register_blueprint(test_bp)


# Helper functions moved to backend/api/test_routes.py where they are used


# Flask routes
@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index_clean.html')

@app.route('/original')
def original_index():
    """Serve the original monolithic page for comparison"""
    return render_template('index.html')


@app.route('/test')
def test_page():
    """Serve the API test dashboard"""
    return render_template('test.html')


@app.route('/data_monitor')
def data_monitor_page():
    """Serve the API test dashboard"""
    return render_template('data_monitor.html')


# Main API routes now handled by backend/api/routes.py blueprint


# Test API endpoints now handled by backend/api/test_routes.py blueprint

# WebSocket handlers now managed by backend/api/websocket.py


if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    import os

    if not os.path.exists('templates'):
        os.makedirs('templates')

    # Start background data fetching service
    background_updater.start()

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
        port=5001,  # Changed from 5000 to avoid conflict with Apple AirPlay
        debug=True,
        use_reloader=False,  # Disable reloader to prevent double thread creation
        allow_unsafe_werkzeug=True  # Allow for development on Mac
    )
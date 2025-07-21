#!/usr/bin/env python3
"""
WebSocket handlers for SF Transit Tracker
Handles real-time communication between server and clients
"""

import logging
from flask import request
from flask_socketio import emit

# Import the global instances (will be injected by main app)
data_fetcher = None

logger = logging.getLogger(__name__)


def init_websocket_handlers(df, socketio_instance):
    """Initialize WebSocket handlers with global instances"""
    global data_fetcher
    data_fetcher = df
    
    # Register the handlers with the socketio instance
    socketio_instance.on_event('connect', handle_connect)
    socketio_instance.on_event('disconnect', handle_disconnect)


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


def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {request.sid}")
#!/usr/bin/env python3
"""
Socket.IO Connection Handlers for SF Transit Tracker

IMPORTANT: Despite the filename, this uses Socket.IO HTTP polling, NOT WebSockets!
Socket.IO automatically falls back to HTTP polling when WebSocket libraries are unavailable.
This provides the same connection tracking functionality via HTTP long-polling.

Handles real-time communication and connection-based API triggering:
- Tracks when clients connect/disconnect via HTTP polling
- Starts background API calls only when clients are connected
- Stops API calls when no clients remain (saves 96% API quota)
"""

import logging
from flask import request
from flask_socketio import emit

# Import the global instances (will be injected by main app)
data_fetcher = None
background_updater = None

# Connection tracking for Socket.IO HTTP polling connections
# Note: These are persistent HTTP polling connections, not WebSocket connections
active_connections = 0

logger = logging.getLogger(__name__)


def init_websocket_handlers(df, socketio_instance, bg_updater=None):
    """Initialize Socket.IO connection handlers (HTTP polling, not WebSockets)"""
    global data_fetcher, background_updater
    data_fetcher = df
    background_updater = bg_updater
    
    # Register the handlers with the socketio instance
    socketio_instance.on_event('connect', handle_connect)
    socketio_instance.on_event('disconnect', handle_disconnect)


def handle_connect():
    """Handle Socket.IO client connection (via HTTP polling)"""
    global active_connections
    active_connections += 1
    logger.info(f"🔌 Socket.IO client connected via HTTP polling: {request.sid} (total connections: {active_connections})")

    # Start background updater if this is the first connection
    if active_connections == 1 and background_updater and not background_updater.is_running:
        logger.info("Starting background updater - first client connected")
        background_updater.start()
        # Force immediate update for new client
        background_updater.force_update()
    elif data_fetcher.vehicles:
        # Send current data to new client
        emit('bulk_update', {
            'vehicles': [vehicle.to_dict() for vehicle in data_fetcher.vehicles.values()],
            'timestamp': data_fetcher.last_update.isoformat() if data_fetcher.last_update else None,
            'count': len(data_fetcher.vehicles)
        })


def handle_disconnect():
    """Handle Socket.IO client disconnection (HTTP polling session ended)"""
    global active_connections
    active_connections = max(0, active_connections - 1)
    logger.info(f"Socket.IO client disconnected: {request.sid} (total connections: {active_connections})")

    # Stop background updater if no clients remain
    if active_connections == 0 and background_updater and background_updater.is_running:
        logger.info("Stopping background updater - no clients connected")
        background_updater.stop()
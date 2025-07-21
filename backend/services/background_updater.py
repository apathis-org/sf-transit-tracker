#!/usr/bin/env python3
"""
Background Update Service for SF Transit Tracker
Handles continuous data fetching and WebSocket broadcasting
"""

import time
import threading
import logging
from datetime import datetime
from typing import Optional
from flask_socketio import SocketIO

from backend.services.transit_fetcher import TransitDataFetcher

logger = logging.getLogger(__name__)


class BackgroundUpdater:
    """
    Background service that continuously fetches transit data and broadcasts updates
    """
    
    def __init__(self, data_fetcher: TransitDataFetcher, socketio: SocketIO, update_interval: int = 30):
        """
        Initialize the background updater
        
        Args:
            data_fetcher: TransitDataFetcher instance
            socketio: Flask-SocketIO instance for broadcasting
            update_interval: Update interval in seconds (default: 30)
        """
        self.data_fetcher = data_fetcher
        self.socketio = socketio
        self.update_interval = update_interval
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
    
    def start(self):
        """Start the background update thread"""
        if self.is_running:
            logger.warning("Background updater is already running")
            return
        
        self.is_running = True
        self.thread = threading.Thread(target=self._update_loop, daemon=True)
        self.thread.start()
        logger.info(f"Background updater started with {self.update_interval}s interval")
    
    def stop(self):
        """Stop the background update thread"""
        self.is_running = False
        if self.thread and self.thread.is_alive():
            logger.info("Stopping background updater...")
            # Thread will stop on next iteration
    
    def _update_loop(self):
        """Main update loop - runs in background thread"""
        while self.is_running:
            try:
                logger.info("Fetching transit data...")
                start_time = time.time()

                vehicles = self.data_fetcher.fetch_all_data()

                fetch_time = (time.time() - start_time) * 1000  # Convert to milliseconds

                # Emit to all connected clients
                self.socketio.emit('bulk_update', {
                    'vehicles': [vehicle.to_dict() for vehicle in vehicles.values()],
                    'timestamp': self.data_fetcher.last_update.isoformat(),
                    'fetchTime': fetch_time,
                    'count': len(vehicles)
                })

                logger.info(f"Updated {len(vehicles)} vehicles in {fetch_time:.0f}ms")

            except Exception as e:
                logger.error(f"Error in background update: {e}")
                self.socketio.emit('error', {
                    'message': f'Data fetch error: {str(e)}',
                    'timestamp': datetime.now().isoformat()
                })

            # Wait for next update
            time.sleep(self.update_interval)
    
    def force_update(self):
        """Force an immediate update (useful for testing)"""
        try:
            logger.info("Force updating transit data...")
            start_time = time.time()

            vehicles = self.data_fetcher.fetch_all_data()

            fetch_time = (time.time() - start_time) * 1000

            # Emit to all connected clients
            self.socketio.emit('bulk_update', {
                'vehicles': [vehicle.to_dict() for vehicle in vehicles.values()],
                'timestamp': self.data_fetcher.last_update.isoformat(),
                'fetchTime': fetch_time,
                'count': len(vehicles)
            })

            logger.info(f"Force updated {len(vehicles)} vehicles in {fetch_time:.0f}ms")
            return True

        except Exception as e:
            logger.error(f"Error in force update: {e}")
            self.socketio.emit('error', {
                'message': f'Force update error: {str(e)}',
                'timestamp': datetime.now().isoformat()
            })
            return False
"""
Transit data fetching service for SF Transit Tracker
Handles API calls to 511.org GTFS-Realtime and BART APIs
"""

import os
import requests
import logging
from datetime import datetime
from typing import Dict, List, Optional

# Import our models
from backend.models.vehicle import Vehicle

# GTFS Realtime imports
try:
    from google.transit import gtfs_realtime_pb2
except ImportError:
    print("Installing gtfs-realtime-bindings...")
    os.system("pip install gtfs-realtime-bindings")
    from google.transit import gtfs_realtime_pb2

# Get logger
logger = logging.getLogger(__name__)


class TransitDataFetcher:
    """Handles fetching data from various transit APIs"""

    def __init__(self, api_keys: Dict[str, str]):
        self.vehicles: Dict[str, Vehicle] = {}
        self.last_update = None
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SF-Transit-Tracker/1.0'
        })
        self.api_keys = api_keys

    def fetch_511_gtfs_data(self, api_key: str) -> List[Vehicle]:
        """Fetch GTFS-Realtime data from 511.org"""
        vehicles = []
        agencies = ['SF', 'GG', 'AC', 'RG']  # SFMTA, Golden Gate, AC Transit, Regional

        for agency in agencies:
            try:
                # Updated endpoint URL (lowercase)
                url = "http://api.511.org/transit/vehiclepositions"
                params = {
                    'api_key': api_key,
                    'agency': agency
                }

                response = self.session.get(url, params=params, timeout=15)
                logger.info(f"511 {agency} API Response: {response.status_code}")

                if response.status_code == 200:
                    # Parse GTFS-Realtime protobuf
                    feed = gtfs_realtime_pb2.FeedMessage()
                    feed.ParseFromString(response.content)

                    agency_vehicles = []
                    for entity in feed.entity:
                        if entity.HasField('vehicle') and entity.vehicle.HasField('position'):
                            vehicle = self._parse_gtfs_vehicle(entity.vehicle, agency)
                            if vehicle:
                                agency_vehicles.append(vehicle)
                                vehicles.append(vehicle)

                    logger.info(f"Fetched {len(agency_vehicles)} vehicles from 511 {agency}")
                else:
                    logger.error(f"511 {agency} API error: {response.status_code} - {response.text}")

            except Exception as e:
                logger.error(f"Error fetching 511 {agency} data: {e}")

        return vehicles

    def _parse_gtfs_vehicle(self, vehicle_data, agency: str) -> Optional[Vehicle]:
        """Parse GTFS vehicle data into Vehicle object"""
        try:
            position = vehicle_data.position

            # Determine vehicle type based on route and agency
            route_id = vehicle_data.trip.route_id if vehicle_data.HasField('trip') else ''
            vehicle_type = self._get_vehicle_type(route_id, agency)

            return Vehicle(
                id=f"{agency.lower()}-{vehicle_data.vehicle.id}",
                type=vehicle_type,
                route=self._format_route(route_id),
                lat=position.latitude,
                lng=position.longitude,
                heading=position.bearing if position.HasField('bearing') else 0.0,
                speed=position.speed * 2.237 if position.HasField('speed') else 15.0,  # m/s to mph
                agency=self._get_agency_name(agency),
                last_update=datetime.now().isoformat()
            )
        except Exception as e:
            logger.error(f"Error parsing GTFS vehicle: {e}")
            return None

    # NextMuni integration removed - 511.org provides comprehensive SFMTA data

    def fetch_bart_data(self, api_key: str) -> List[Vehicle]:
        """Fetch BART data and simulate positions"""
        vehicles = []
        try:
            url = "https://api.bart.gov/api/etd.aspx"
            params = {
                'cmd': 'etd',
                'orig': 'ALL',
                'key': api_key,
                'json': 'y'
            }

            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                vehicles = self._simulate_bart_positions(data)
                logger.info(f"Generated {len(vehicles)} BART vehicles")

        except Exception as e:
            logger.error(f"Error fetching BART data: {e}")

        return vehicles

    def _simulate_bart_positions(self, bart_data: dict) -> List[Vehicle]:
        """Simulate BART train positions based on departure data"""
        vehicles = []

        # BART station coordinates
        stations = {
            '12TH': (37.8034, -122.2711), '16TH': (37.7648, -122.4095),
            '19TH': (37.8081, -122.2690), '24TH': (37.7527, -122.4184),
            'ASHB': (37.8531, -122.2701), 'BALB': (37.7217, -122.4474),
            'CIVC': (37.7795, -122.4136), 'COLM': (37.6847, -122.4661),
            'DALY': (37.7061, -122.4694), 'EMBR': (37.7928, -122.3968),
            'GLEN': (37.7329, -122.4340), 'MONT': (37.7894, -122.4014),
            'POWL': (37.7844, -122.4079)
        }

        try:
            if 'root' in bart_data and 'station' in bart_data['root']:
                stations_data = bart_data['root']['station']
                if not isinstance(stations_data, list):
                    stations_data = [stations_data]

                for station in stations_data:
                    station_abbr = station.get('abbr', '')
                    if station_abbr in stations and 'etd' in station:

                        etd_list = station['etd']
                        if not isinstance(etd_list, list):
                            etd_list = [etd_list]

                        for destination in etd_list:
                            if 'estimate' in destination:
                                estimates = destination['estimate']
                                if not isinstance(estimates, list):
                                    estimates = [estimates]

                                for i, estimate in enumerate(estimates[:2]):  # Max 2 trains per destination
                                    if estimate.get('minutes') != 'Leaving':
                                        lat, lng = stations[station_abbr]

                                        vehicle = Vehicle(
                                            id=f"bart-{station_abbr}-{destination.get('destination', '')}-{i}",
                                            type='bart-train',
                                            route=destination.get('abbreviation',
                                                                  destination.get('destination', '')[:4]),
                                            lat=lat + (hash(f"{station_abbr}{i}") % 100 - 50) * 0.0001,
                                            lng=lng + (hash(
                                                f"{destination.get('destination', '')}{i}") % 100 - 50) * 0.0001,
                                            heading=hash(destination.get('destination', '')) % 360,
                                            speed=35 + (hash(f"{station_abbr}{i}") % 20),
                                            agency='BART',
                                            destination=destination.get('destination', ''),
                                            last_update=datetime.now().isoformat()
                                        )
                                        vehicles.append(vehicle)
        except Exception as e:
            logger.error(f"Error simulating BART positions: {e}")

        return vehicles

    def _get_vehicle_type(self, route_id: str, agency: str) -> str:
        """Determine vehicle type based on route and agency"""
        if agency == 'SF':
            if route_id in ['J', 'K', 'L', 'M', 'N', 'T']:
                return 'light-rail'
            elif route_id in ['PH', 'PM', 'CA']:
                return 'cable-car'
            else:
                return 'muni-bus'
        elif agency == 'GG':
            return 'ferry' if 'ferry' in route_id.lower() else 'bus'
        else:
            return 'bus'

    # NextMuni vehicle type parsing removed - no longer needed

    def _format_route(self, route_id: str) -> str:
        """Format route ID for display"""
        return route_id.replace('_', '').replace('-', '')

    def _get_agency_name(self, agency_code: str) -> str:
        """Get full agency name"""
        names = {
            'SF': 'SFMTA',
            'GG': 'Golden Gate',
            'AC': 'AC Transit'
        }
        return names.get(agency_code, agency_code)

    def fetch_all_data(self) -> Dict[str, Vehicle]:
        """Fetch data from all sources"""
        all_vehicles = {}

        # Fetch from 511.org (primary data source)
        if self.api_keys['SF_511'] != 'YOUR_511_API_KEY':
            vehicles_511 = self.fetch_511_gtfs_data(self.api_keys['SF_511'])
            for vehicle in vehicles_511:
                all_vehicles[vehicle.id] = vehicle

        # NextMuni integration removed - 511.org now provides comprehensive SFMTA data

        # Fetch BART data
        if self.api_keys['BART'] != 'YOUR_BART_API_KEY':
            vehicles_bart = self.fetch_bart_data(self.api_keys['BART'])
            for vehicle in vehicles_bart:
                all_vehicles[vehicle.id] = vehicle

        self.vehicles = all_vehicles
        self.last_update = datetime.now()

        return all_vehicles
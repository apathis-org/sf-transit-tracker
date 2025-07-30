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
        agencies = ['SF', 'RG']  # SFMTA, Regional (includes all Bay Area agencies)

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

            # Try to get route from trip data first
            route_id = ''
            if vehicle_data.HasField('trip') and vehicle_data.trip.HasField('route_id'):
                route_id = vehicle_data.trip.route_id
                logger.debug(f"Vehicle {vehicle_data.vehicle.id} has route_id: {route_id}")
            else:
                # 511.org GTFS feed doesn't include trip data, use vehicle label as route fallback
                if hasattr(vehicle_data.vehicle, 'label') and vehicle_data.vehicle.label:
                    route_id = vehicle_data.vehicle.label
                    logger.debug(f"Vehicle {vehicle_data.vehicle.id} using label as route: {route_id}")
                else:
                    # Last fallback: use part of vehicle ID
                    route_id = vehicle_data.vehicle.id
                    logger.debug(f"Vehicle {vehicle_data.vehicle.id} using ID as route: {route_id}")
            
            # For RG (Regional) feed, extract actual agency from route_id
            actual_agency = agency
            if agency == 'RG':
                if ':' in route_id:
                    # RG feed format: "AGENCY:ROUTE" (e.g., "CT:123", "VTA:22")
                    agency_code, route_part = route_id.split(':', 1)
                    actual_agency = agency_code
                    route_id = route_part  # Use just the route part
                    logger.debug(f"RG vehicle {vehicle_data.vehicle.id}: extracted agency={agency_code}, route={route_part}")
                else:
                    # Fallback for RG vehicles without colon - log and use 'RG' as agency
                    logger.warning(f"RG vehicle {vehicle_data.vehicle.id} has route_id without colon: {route_id}")
                    actual_agency = 'RG'  # Will be mapped by _get_agency_name()
            
            vehicle_type = self._get_vehicle_type(route_id, actual_agency)

            # Extract individual vehicle timestamp if available, fallback to current time
            if vehicle_data.HasField('timestamp'):
                try:
                    # Use the actual vehicle timestamp from GTFS data (Unix timestamp)
                    vehicle_last_update = datetime.fromtimestamp(vehicle_data.timestamp).isoformat()
                    logger.debug(f"Vehicle {vehicle_data.vehicle.id} using GTFS timestamp: {vehicle_last_update}")
                except (ValueError, OSError) as e:
                    # Handle invalid timestamp values
                    logger.warning(f"Invalid timestamp {vehicle_data.timestamp} for vehicle {vehicle_data.vehicle.id}: {e}")
                    vehicle_last_update = datetime.now().isoformat()
            else:
                # Fallback to current time if no timestamp in GTFS data
                vehicle_last_update = datetime.now().isoformat()
                logger.debug(f"Vehicle {vehicle_data.vehicle.id} using fallback timestamp: {vehicle_last_update}")

            return Vehicle(
                id=f"{agency.lower()}-{vehicle_data.vehicle.id}",
                type=vehicle_type,
                route=self._format_route(route_id),
                lat=position.latitude,
                lng=position.longitude,
                heading=position.bearing if position.HasField('bearing') else 0.0,
                speed=position.speed * 2.237 if position.HasField('speed') else 15.0,  # m/s to mph
                agency=self._get_agency_name(actual_agency),
                last_update=vehicle_last_update
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
        """Determine vehicle type based on route and agency - expanded for Bay Area Regional"""
        if agency == 'SF':
            if route_id in ['J', 'K', 'L', 'M', 'N', 'T']:
                return 'light-rail'
            elif route_id in ['PH', 'PM', 'CA']:
                return 'cable-car'
            else:
                return 'muni-bus'
        elif agency == 'GG':
            return 'ferry' if 'ferry' in route_id.lower() else 'bus'
        # Bay Area Regional agencies
        elif agency in ['CT', 'AM', 'CE', 'SA']:  # Train agencies
            return 'train'
        elif agency == 'SB':  # SF Bay Ferry
            return 'ferry'
        elif agency in ['3D', 'CC', 'WC']:  # Agencies with express buses
            # Check if route indicates express service
            if 'express' in route_id.lower() or 'x' in route_id.lower():
                return 'express-bus'
            else:
                return 'bus'
        else:
            return 'bus'

    # NextMuni vehicle type parsing removed - no longer needed

    def _format_route(self, route_id: str) -> str:
        """Format route ID for display"""
        return route_id.replace('_', '').replace('-', '')

    def _get_agency_name(self, agency_code: str) -> str:
        """Get full agency name - expanded to include all Bay Area Regional agencies"""
        names = {
            'SF': 'SFMTA',
            'GG': 'Golden Gate', 
            'AC': 'AC Transit',
            'RG': 'Regional',
            # Bay Area Regional agencies from RG feed
            '3D': 'Tri Delta Transit',
            'AM': 'Capitol Corridor',
            'CC': 'County Connection', 
            'CE': 'Altamont Corridor Express',
            'CT': 'Caltrain',
            'DE': 'Dumbarton Express',
            'EM': 'Emery Go-Round',
            'FS': 'FS Transit',
            'MA': 'Marin Transit',
            'MV': 'MV Transportation',
            'PG': 'Presidio Go',
            'SA': 'SMART',
            'SB': 'SF Bay Ferry',
            'SC': 'VTA',
            'SM': 'SamTrans',
            'SO': 'Sonoma County Transit',
            'SR': 'Sonoma County Transit (SR)',
            'ST': 'SolTrans',
            'UC': 'Union City Transit',
            'VC': 'Vacaville City Coach',
            'VN': 'Vine Transit',
            'WC': 'WestCAT',
            'WH': 'Wheels'
        }
        mapped_name = names.get(agency_code, agency_code)
        if mapped_name == agency_code and agency_code not in names:
            logger.warning(f"Unknown agency code encountered: {agency_code} - using as-is")
        return mapped_name

    def fetch_all_data(self) -> Dict[str, Vehicle]:
        """Fetch data from all sources with deduplication"""
        all_vehicles = {}
        sf_vehicle_ids = set()

        # Fetch from 511.org (primary data source)
        if self.api_keys['SF_511'] != 'YOUR_511_API_KEY':
            vehicles_511 = self.fetch_511_gtfs_data(self.api_keys['SF_511'])
            for vehicle in vehicles_511:
                all_vehicles[vehicle.id] = vehicle
                
                # Track SF vehicle IDs for deduplication
                if vehicle.agency == 'SFMTA':
                    # Extract original vehicle ID from our prefixed ID
                    original_id = vehicle.id.replace('sf-', '')
                    sf_vehicle_ids.add(original_id)

        # NextMuni integration removed - 511.org now provides comprehensive SFMTA data

        # Fetch BART data
        if self.api_keys['BART'] != 'YOUR_BART_API_KEY':
            vehicles_bart = self.fetch_bart_data(self.api_keys['BART'])
            for vehicle in vehicles_bart:
                all_vehicles[vehicle.id] = vehicle

        # Deduplicate: Remove RG vehicles that are duplicates of SF vehicles
        # SF vehicles take priority as they have more accurate route information
        vehicles_to_remove = []
        for vehicle_id, vehicle in all_vehicles.items():
            if vehicle.id.startswith('rg-') and hasattr(vehicle, 'agency'):
                # Check if this RG vehicle is actually an SF vehicle
                original_id = vehicle.id.replace('rg-', '')
                if original_id in sf_vehicle_ids:
                    vehicles_to_remove.append(vehicle_id)
                    logger.debug(f"Removing duplicate RG vehicle: {vehicle_id} (duplicate of SF vehicle)")

        for vehicle_id in vehicles_to_remove:
            del all_vehicles[vehicle_id]

        logger.info(f"Deduplication removed {len(vehicles_to_remove)} duplicate vehicles")

        self.vehicles = all_vehicles
        self.last_update = datetime.now()

        return all_vehicles
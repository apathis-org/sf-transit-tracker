#!/usr/bin/env python3
"""
Enhanced SF Transit API Testing Script - Route-Level Analysis
Analyzes individual transport lines within each agency
"""

import os
import time
import requests
import xmltodict
import zipfile
import io
import csv
from collections import defaultdict
from dotenv import load_dotenv

# GTFS Realtime imports
try:
    from google.transit import gtfs_realtime_pb2
except ImportError:
    print("Installing gtfs-realtime-bindings...")
    os.system("pip install gtfs-realtime-bindings")
    from google.transit import gtfs_realtime_pb2

# Load environment variables
load_dotenv()


class EnhancedAPITester:
    def __init__(self):
        self.api_keys = {
            'SF_511': os.getenv('SF_511_API_KEY', 'YOUR_511_API_KEY'),
            'BART': os.getenv('BART_API_KEY', 'YOUR_BART_API_KEY')
        }
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'SF-Transit-Tracker-Enhanced/1.0'})

        # Store detailed route data
        self.route_data = defaultdict(lambda: defaultdict(list))

        # Cache for route names
        self.route_names = defaultdict(dict)  # {agency: {route_id: full_name}}

    def print_header(self, title):
        print(f"\n{'=' * 70}")
        print(f"🔍 {title}")
        print(f"{'=' * 70}")

    def print_agency_header(self, agency_name, agency_code):
        print(f"\n🚌 {agency_name} ({agency_code})")
        print("-" * 50)

    def print_route_info(self, agency_code, route_id, vehicle_count, route_type, destinations=None):
        """Print route information with full name"""
        type_icon = {
            'muni-bus': '🚌',
            'light-rail': '🚊',
            'cable-car': '🚡',
            'bart-train': '🚇',
            'ferry': '⛴️',
            'bus': '🚌'
        }.get(route_type, '🚌')

        # Get full route name
        full_name = self.get_route_display_name(agency_code, route_id)
        display_name = full_name if full_name != route_id else route_id

        print(f"  {type_icon} {display_name:<20} {vehicle_count:>3} vehicles", end="")
        if destinations:
            print(f" → {', '.join(destinations[:2])}")
        else:
            print()

    def load_gtfs_route_names(self, agency_code):
        """Load route names from GTFS static data"""
        if agency_code in self.route_names and self.route_names[agency_code]:
            return  # Already loaded

        try:
            # Simplified: Use known route names for SF agency
            if agency_code == 'SF':
                sf_routes = {
                    # Light Rail
                    'J': 'J-Church', 'K': 'K-Ingleside', 'L': 'L-Taraval',
                    'M': 'M-Ocean View', 'N': 'N-Judah', 'T': 'T-Third Street',
                    # Cable Cars
                    'PH': 'Powell-Hyde', 'PM': 'Powell-Mason', 'CA': 'California',
                    # Muni Buses (comprehensive list)
                    '1': '1-California', '1X': '1X-California Express', '2': '2-Clement', '3': '3-Jackson',
                    '5': '5-Fulton', '5R': '5R-Fulton Rapid', '6': '6-Haight-Parnassus', '7': '7-Haight/Noriega',
                    '8': '8-Bayshore', '8BX': '8BX-Bayshore B Express', '9': '9-San Bruno', '9R': '9R-San Bruno Rapid',
                    '10': '10-Townsend', '12': '12-Folsom/Pacific', '14': '14-Mission', '14R': '14R-Mission Rapid',
                    '15': '15-Kearny', '16': '16-Noriega', '17': '17-Parkmerced', '18': '18-46th Avenue',
                    '19': '19-Polk', '20': '20-Columbus', '21': '21-Hayes', '22': '22-Fillmore',
                    '23': '23-Monterey', '24': '24-Divisadero', '25': '25-Treasure Island',
                    '27': '27-Bryant', '28': '28-19th Avenue', '28R': '28R-19th Avenue Rapid',
                    '29': '29-Sunset', '30': '30-Stockton', '31': '31-Balboa',
                    '33': '33-Ashbury/18th', '35': '35-Eureka', '36': '36-Teresita',
                    '37': '37-Corbett', '38': '38-Geary', '38R': '38R-Geary Rapid',
                    '39': '39-Coit', '43': '43-Masonic', '44': '44-O\'Shaughnessy',
                    '45': '45-Union/Stockton', '47': '47-Van Ness', '48': '48-Quintara/24th Street',
                    '49': '49-Mission/Van Ness', '52': '52-Excelsior', '54': '54-Felton',
                    '55': '55-16th Street', '56': '56-Rutland', '57': '57-Parkmerced',
                    '58': '58-24th Street', '66': '66-Quintara', '67': '67-Bernal Heights',
                    '71': '71-Haight/Noriega', '76': '76-Marin/Headlands', '81': '81-Caltrain',
                    '82': '82-Levi Plaza', '83': '83-Alemany', '88': '88-BART Shuttle',
                    '90': '90-San Bruno Owl', '91': '91-Owl', '108': '108-Treasure Island'
                }
                self.route_names[agency_code] = sf_routes

            elif agency_code == 'GG':
                gg_routes = {
                    # Golden Gate Transit Buses
                    '101': '101-San Rafael/SF Express', '130': '130-San Rafael/SF Basic',
                    '140': '140-San Rafael/SF Mill Valley', '150': '150-San Rafael/SF Novato',
                    '160': '160-Petaluma/SF Express', '170': '170-Sonoma County/SF',
                    '24': '24-San Rafael Local', '27': '27-San Rafael/Mill Valley',
                    '35': '35-Tiburon/Sausalito', '4': '4-San Rafael/Larkspur',
                    '4C': '4C-Larkspur/Corte Madera', '8': '8-San Rafael/Novato',
                    # Ferry Routes
                    'SF-SAU': 'SF-Sausalito Ferry', 'SF-TIB': 'SF-Tiburon Ferry',
                    'SF-LAR': 'SF-Larkspur Ferry'
                }
                self.route_names[agency_code] = gg_routes

            elif agency_code == 'AC':
                ac_routes = {
                    # AC Transit Local Routes
                    '1': '1-Fremont/Union City Local', '6': '6-Fremont BART Shuttle',
                    '18': '18-Berkeley Local', '20': '20-Berkeley/Emeryville',
                    '51A': '51A-Rockridge BART Shuttle', '72': '72-San Leandro BART Shuttle',
                    '88': '88-MacArthur BART Shuttle', '200': '200-Hayward Local',
                    '232': '232-Hayward/Castro Valley',
                    # Transbay Routes (to SF)
                    'F': 'F-Transbay Fremont', 'FS': 'FS-Transbay Fremont Express',
                    'G': 'G-Transbay Albany', 'NL': 'NL-Transbay Richmond',
                    'O': 'O-Transbay Oakland', 'P': 'P-Transbay Rockridge',
                    'T': 'T-Transbay Berkeley', 'TE': 'TE-Transbay Berkeley Express',
                    'U': 'U-Transbay San Leandro', 'V': 'V-Transbay Antioch',
                    'W': 'W-Transbay Walnut Creek', 'Z': 'Z-Transbay Union City'
                }
                self.route_names[agency_code] = ac_routes

        except Exception as e:
            pass  # Fail silently, use route IDs as fallback

    def get_route_display_name(self, agency_code, route_id):
        """Get full route name or fallback to route_id"""
        return self.route_names.get(agency_code, {}).get(route_id, route_id)
        type_icon = {
            'muni-bus': '🚌',
            'light-rail': '🚊',
            'cable-car': '🚡',
            'bart-train': '🚇',
            'ferry': '⛴️',
            'bus': '🚌'
        }.get(route_type, '🚌')

        print(f"  {type_icon} {route_id:<15} {vehicle_count:>3} vehicles", end="")
        if destinations:
            print(f" → {', '.join(destinations[:2])}")
        else:
            print()

    def analyze_511_routes(self):
        """Analyze individual routes from 511.org"""
        self.print_header("511.org Route Analysis")

        agencies = {
            'SF': 'San Francisco Municipal Transportation (SFMTA)',
            'GG': 'Golden Gate Transit',
            'AC': 'AC Transit (Alameda-Contra Costa)',
            'RG': 'Regional (All Bay Area Agencies)'
        }

        total_routes = 0
        total_vehicles = 0

        for agency_code, agency_name in agencies.items():
            try:
                self.print_agency_header(agency_name, agency_code)

                # Load GTFS route names first
                self.load_gtfs_route_names(agency_code)

                url = "http://api.511.org/transit/vehiclepositions"
                params = {
                    'api_key': self.api_keys['SF_511'],
                    'agency': agency_code
                }

                response = self.session.get(url, params=params, timeout=15)

                if response.status_code == 200:
                    # Parse GTFS-Realtime data
                    feed = gtfs_realtime_pb2.FeedMessage()
                    feed.ParseFromString(response.content)

                    # Group vehicles by route
                    routes = defaultdict(lambda: {'count': 0, 'vehicles': [], 'destinations': set()})

                    for entity in feed.entity:
                        if entity.HasField('vehicle') and entity.vehicle.HasField('position'):
                            vehicle = entity.vehicle
                            route_id = vehicle.trip.route_id if vehicle.HasField('trip') else 'Unknown'

                            # Skip unknown/empty routes
                            if not route_id or route_id in ['Unknown', '', None]:
                                continue

                            # Determine vehicle type
                            vehicle_type = self._get_vehicle_type(route_id, agency_code)

                            # Extract destination/direction if available
                            destination = self._extract_direction(vehicle)

                            routes[route_id]['count'] += 1
                            routes[route_id]['type'] = vehicle_type
                            routes[route_id]['vehicles'].append({
                                'id': vehicle.vehicle.id,
                                'lat': vehicle.position.latitude,
                                'lng': vehicle.position.longitude,
                                'speed': vehicle.position.speed if vehicle.position.HasField('speed') else 0,
                                'heading': vehicle.position.bearing if vehicle.position.HasField('bearing') else 0
                            })
                            if destination:
                                routes[route_id]['destinations'].add(destination)

                    # Sort routes by vehicle count (most active first)
                    sorted_routes = sorted(routes.items(), key=lambda x: x[1]['count'], reverse=True)

                    agency_vehicles = 0
                    agency_routes = len(sorted_routes)

                    # Group by transport type for better organization
                    transport_types = defaultdict(list)
                    for route_id, data in sorted_routes:
                        transport_types[data['type']].append((route_id, data))

                    # Display by transport type
                    for transport_type, type_routes in transport_types.items():
                        print(f"\n  📋 {self._get_transport_type_name(transport_type)}:")
                        for route_id, data in type_routes:
                            destinations = list(data['destinations']) if data['destinations'] else None
                            self.print_route_info(agency_code, route_id, data['count'], transport_type, destinations)
                            agency_vehicles += data['count']

                    print(f"\n  ✅ Total: {agency_routes} routes, {agency_vehicles} vehicles")
                    total_routes += agency_routes
                    total_vehicles += agency_vehicles

                    # Store for later analysis
                    self.route_data[agency_code] = routes

                else:
                    print(f"  ❌ API Error: {response.status_code}")

            except Exception as e:
                print(f"  ❌ Error: {str(e)}")

        print(f"\n🎯 GRAND TOTAL: {total_routes} routes, {total_vehicles} vehicles across all agencies")
        return total_routes > 0

    def analyze_bart_lines(self):
        """Analyze BART lines and stations"""
        self.print_header("BART Line Analysis")

        if self.api_keys['BART'] == 'YOUR_BART_API_KEY':
            print("❌ BART API key not configured")
            return False

        try:
            # Get station list first
            stations_url = "https://api.bart.gov/api/stn.aspx"
            stations_params = {
                'cmd': 'stns',
                'key': self.api_keys['BART'],
                'json': 'y'
            }

            stations_response = self.session.get(stations_url, params=stations_params, timeout=10)

            if stations_response.status_code == 200:
                stations_data = stations_response.json()

                # Get departure data
                etd_url = "https://api.bart.gov/api/etd.aspx"
                etd_params = {
                    'cmd': 'etd',
                    'orig': 'ALL',
                    'key': self.api_keys['BART'],
                    'json': 'y'
                }

                etd_response = self.session.get(etd_url, params=etd_params, timeout=10)

                if etd_response.status_code == 200:
                    etd_data = etd_response.json()

                    # Analyze lines and destinations
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

                    # Display BART lines
                    print("🚇 BART Lines:")
                    total_trains = 0
                    for line_code, data in sorted(lines.items()):
                        destinations = list(data['destinations'])
                        if len(destinations) >= 2:
                            direction_text = f"{destinations[0]} → {destinations[1]}"
                        elif len(destinations) == 1:
                            direction_text = f"→ {destinations[0]}"
                        else:
                            direction_text = "Direction unknown"

                        print(f"  🚇 {line_code:<8} {data['trains']:>3} trains  {direction_text}")
                        print(f"      Serves: {len(data['stations'])} stations")
                        total_trains += data['trains']

                    print(f"\n  ✅ Total: {len(lines)} lines, {total_trains} active trains")
                    return True

        except Exception as e:
            print(f"❌ Error: {str(e)}")

        return False

    def analyze_bart_route_details(self, line_code):
        """Get detailed info for a specific BART line"""
        if self.api_keys['BART'] == 'YOUR_BART_API_KEY':
            print("❌ BART API key not configured")
            return False

        try:
            print(f"\n📊 Detailed BART Line Analysis: {line_code}")
            print("-" * 50)

            # Get departure data for all stations
            etd_url = "https://api.bart.gov/api/etd.aspx"
            etd_params = {
                'cmd': 'etd',
                'orig': 'ALL',
                'key': self.api_keys['BART'],
                'json': 'y'
            }

            etd_response = self.session.get(etd_url, params=etd_params, timeout=10)

            if etd_response.status_code == 200:
                etd_data = etd_response.json()

                line_info = {
                    'stations': set(),
                    'departures': [],
                    'directions': defaultdict(int),
                    'next_trains': []
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

                                # Check if this departure matches our line
                                if abbreviation == line_code or destination.replace(' ', '').upper() == line_code:
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

                # Display results
                if line_info['stations']:
                    # Line overview
                    directions = list(line_info['directions'].keys())
                    if len(directions) >= 2:
                        print(f"🚇 Route: {directions[0]} ↔ {directions[1]}")
                    elif len(directions) == 1:
                        print(f"🚇 Route: → {directions[0]}")

                    print(f"📍 Stations Served: {len(line_info['stations'])}")
                    stations_list = sorted(list(line_info['stations']))
                    for i, station in enumerate(stations_list):
                        print(f"   {i + 1:2}. {station}")

                    # Train counts by direction
                    print(f"\n🚊 Active Trains by Direction:")
                    total_trains = 0
                    for direction, count in line_info['directions'].items():
                        print(f"   → {direction:<25} {count:>3} trains")
                        total_trains += count
                    print(f"   {'Total':<27} {total_trains:>3} trains")

                    # Next departures (upcoming 10)
                    if line_info['departures']:
                        print(f"\n⏰ Next Departures:")
                        print(f"   {'Station':<20} {'Destination':<15} {'Minutes':<8} {'Platform'}")
                        print("   " + "-" * 55)

                        # Sort by minutes (handle 'Leaving' as 0)
                        def sort_key(x):
                            if x['minutes'] == 'Leaving':
                                return 0
                            elif x['minutes'].isdigit():
                                return int(x['minutes'])
                            else:
                                return 999

                        sorted_departures = sorted(line_info['departures'], key=sort_key)

                        for departure in sorted_departures[:10]:  # Show next 10
                            station = departure['station'][:19]
                            destination = departure['destination'][:14]
                            minutes = departure['minutes']
                            platform = departure['platform']

                            print(f"   {station:<20} {destination:<15} {minutes:<8} {platform}")

                    return True
                else:
                    print(f"❌ No active trains found for line '{line_code}'")
                    print("💡 Available line codes: ANTC, DALY, DUBL, FRMT, MLBR, RICH, WARM")
                    return False

        except Exception as e:
            print(f"❌ Error analyzing BART line: {str(e)}")
            return False

    def analyze_route_details(self, agency_code, route_id):
        """Get detailed info for a specific route"""
        agency_names = {
            'SF': 'SFMTA',
            'GG': 'Golden Gate Transit',
            'AC': 'AC Transit',
            'RG': 'Regional'
        }

        if agency_code in self.route_data and route_id in self.route_data[agency_code]:
            route_info = self.route_data[agency_code][route_id]

            print(f"\n📊 Detailed Analysis: {agency_names.get(agency_code, agency_code)} - {route_id}")
            print(f"Vehicle Type: {route_info['type']}")
            print(f"Active Vehicles: {route_info['count']}")
            print(f"Destinations: {', '.join(route_info['destinations']) if route_info['destinations'] else 'Unknown'}")

            if route_info['vehicles']:
                print("\nSample Vehicles:")
                for i, vehicle in enumerate(route_info['vehicles'][:3]):  # Show first 3
                    print(f"  🚌 {vehicle['id']}: ({vehicle['lat']:.4f}, {vehicle['lng']:.4f}) "
                          f"Speed: {vehicle['speed']:.1f} m/s, Heading: {vehicle['heading']}°")

    def _extract_direction(self, vehicle):
        """Extract direction/destination from vehicle data"""
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

    def _get_vehicle_type(self, route_id, agency):
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
        elif agency == 'RG':
            # Regional feed - check for ferry indicators
            if any(ferry_indicator in route_id.lower() for ferry_indicator in
                   ['ferry', 'sausalito', 'tiburon', 'larkspur', 'sf-sau', 'sf-tib', 'sf-lar']):
                return 'ferry'
            elif route_id in ['J', 'K', 'L', 'M', 'N', 'T']:
                return 'light-rail'
            elif route_id.startswith('BART') or route_id in ['ANTC', 'DALY', 'DUBL', 'FRMT', 'MLBR', 'RICH', 'WARM']:
                return 'bart-train'
            else:
                return 'bus'
        else:
            return 'bus'

    def _get_transport_type_name(self, vehicle_type):
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

    def generate_summary_report(self):
        """Generate a comprehensive summary"""
        self.print_header("Summary Report")

        total_agencies = len(self.route_data)
        total_routes = sum(len(routes) for routes in self.route_data.values())
        total_vehicles = sum(
            sum(route['count'] for route in routes.values())
            for routes in self.route_data.values()
        )

        print(f"📊 Agencies Tested: {total_agencies}")
        print(f"📊 Total Routes Found: {total_routes}")
        print(f"📊 Total Active Vehicles: {total_vehicles}")

        # Most active routes across all agencies
        all_routes = []
        for agency_code, routes in self.route_data.items():
            for route_id, data in routes.items():
                all_routes.append((f"{agency_code}-{route_id}", data['count'], data['type']))

        if all_routes:
            print("\n🏆 Most Active Routes:")
            top_routes = sorted(all_routes, key=lambda x: x[1], reverse=True)[:10]
            for i, (route_name, count, route_type) in enumerate(top_routes, 1):
                type_icon = {'muni-bus': '🚌', 'light-rail': '🚊', 'cable-car': '🚡', 'bus': '🚌'}.get(route_type, '🚌')
                print(f"  {i:2}. {type_icon} {route_name:<15} {count:>3} vehicles")

    def run_enhanced_tests(self):
        """Run comprehensive route analysis"""
        print("🔍 Enhanced SF Transit Route Analysis")
        print("=" * 70)

        # Test APIs with route-level detail
        routes_found = self.analyze_511_routes()
        bart_found = self.analyze_bart_lines()

        if routes_found or bart_found:
            self.generate_summary_report()

            # Offer detailed analysis of specific routes
            print(f"\n💡 To analyze a specific route, call:")
            print(f"   tester.analyze_route_details('SF', '38')  # For route 38")
            print(f"   tester.analyze_route_details('SF', 'J')   # For J-Church line")

        return routes_found or bart_found


def main():
    """Run enhanced testing"""
    tester = EnhancedAPITester()

    # Run the enhanced analysis
    success = tester.run_enhanced_tests()

    if success:
        print(f"\n🎉 Enhanced analysis complete!")
        print(f"✅ You now have detailed route information for your transit tracker!")
    else:
        print(f"\n⚠️ Some tests failed - check your API keys in .env file")
    tester.analyze_route_details('SF', '38')
    return tester  # Return tester object for interactive use


if __name__ == "__main__":
    tester = main()
#!/usr/bin/env python3
"""
SF Transit API Testing Script for PyCharm
Run this directly in PyCharm to test all APIs before updating the server
"""

import os
import time
import requests
import xmltodict
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


class APITester:
    def __init__(self):
        self.api_keys = {
            'SF_511': os.getenv('SF_511_API_KEY', 'YOUR_511_API_KEY'),
            'BART': os.getenv('BART_API_KEY', 'YOUR_BART_API_KEY')
        }
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'SF-Transit-Tracker-Test/1.0'})

    def print_header(self, title):
        print(f"\n{'=' * 60}")
        print(f"🧪 {title}")
        print(f"{'=' * 60}")

    def print_result(self, test_name, success, details):
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        print(f"    {details}")

    def test_511_api(self):
        """Test 511.org API with corrected endpoint"""
        self.print_header("Testing 511.org API")

        if self.api_keys['SF_511'] == 'YOUR_511_API_KEY':
            self.print_result("511.org API", False, "API key not configured in .env file")
            return False

        agencies = ['SF', 'GG', 'AC', 'RG']
        total_vehicles = 0

        for agency in agencies:
            try:
                print(f"\n🔍 Testing agency: {agency}")
                url = "http://api.511.org/transit/vehiclepositions"
                params = {
                    'api_key': self.api_keys['SF_511'],
                    'agency': agency
                }

                start_time = time.time()
                response = self.session.get(url, params=params, timeout=15)
                response_time = (time.time() - start_time) * 1000

                print(f"    Response: {response.status_code}")
                print(f"    Content length: {len(response.content)} bytes")
                print(f"    Response time: {response_time:.0f}ms")
                #print(f"    Content : {response.content}")

                if response.status_code == 200:
                    # Parse GTFS-Realtime data
                    feed = gtfs_realtime_pb2.FeedMessage()
                    feed.ParseFromString(response.content)

                    agency_vehicles = 0
                    for entity in feed.entity:
                        if entity.HasField('vehicle') and entity.vehicle.HasField('position'):
                            agency_vehicles += 1

                    total_vehicles += agency_vehicles
                    self.print_result(f"511 {agency}", True,
                                      f"{agency_vehicles} vehicles found, {response_time:.0f}ms")

                    # Show sample vehicle data
                    if agency_vehicles > 0 and agency == 'SF':
                        entity = feed.entity[0]
                        if entity.HasField('vehicle'):
                            vehicle = entity.vehicle
                            route = vehicle.trip.route_id if vehicle.HasField('trip') else 'Unknown'
                            pos = vehicle.position
                            print(f"    Sample vehicle: Route {route} at ({pos.latitude:.4f}, {pos.longitude:.4f})")
                else:
                    self.print_result(f"511 {agency}", False,
                                      f"HTTP {response.status_code}: {response.text[:100]}")

            except Exception as e:
                self.print_result(f"511 {agency}", False, f"Exception: {str(e)}")

        print(f"\n🎯 TOTAL 511.org VEHICLES: {total_vehicles}")
        return total_vehicles > 0

    def test_nextmuni_api(self):
        """Test NextMuni API with multiple agency attempts"""
        self.print_header("Testing NextMuni API")

        # First, get available agencies
        try:
            agency_url = "https://retro.umoiq.com/service/publicXMLFeed?command=agencyList"
            agency_response = self.session.get(agency_url, timeout=10)

            print(f"Agency list response: {agency_response.status_code}")
            if agency_response.status_code == 200:
                print("Available agencies:")
                print(agency_response.text[:500])

                # Parse agencies
                try:
                    agency_data = xmltodict.parse(agency_response.text)
                    if 'body' in agency_data and 'agency' in agency_data['body']:
                        agencies = agency_data['body']['agency']
                        if isinstance(agencies, list):
                            sf_agencies = [a for a in agencies if 'sf' in str(a).lower() or 'muni' in str(a).lower()]
                            print(f"SF-related agencies found: {sf_agencies}")
                except Exception as e:
                    print(f"Error parsing agencies: {e}")
        except Exception as e:
            print(f"Error getting agency list: {e}")

        # Try different agency tags
        possible_agencies = ['sf-muni', 'sfmuni', 'muni', 'SF', 'sf']

        for agency_tag in possible_agencies:
            try:
                print(f"\n🔍 Testing NextMuni agency: {agency_tag}")
                url = "https://retro.umoiq.com/service/publicXMLFeed"
                params = {
                    'command': 'vehicleLocations',
                    'a': agency_tag,
                    't': '0'
                }

                start_time = time.time()
                response = self.session.get(url, params=params, timeout=10)
                response_time = (time.time() - start_time) * 1000

                print(f"    Response: {response.status_code}")
                print(f"    Content length: {len(response.text)} chars")
                print(f"    Response time: {response_time:.0f}ms")

                if response.status_code == 200:
                    print(f"    First 200 chars: {response.text[:200]}")

                    data = xmltodict.parse(response.text)

                    # Check for error
                    if 'Error' in str(data):
                        self.print_result(f"NextMuni {agency_tag}", False,
                                          f"API Error: {data}")
                        continue

                    # Check for vehicles
                    vehicle_count = 0
                    if 'body' in data and 'vehicle' in data['body']:
                        vehicles = data['body']['vehicle']
                        if isinstance(vehicles, list):
                            vehicle_count = len(vehicles)
                        else:
                            vehicle_count = 1

                    if vehicle_count > 0:
                        self.print_result(f"NextMuni {agency_tag}", True,
                                          f"{vehicle_count} vehicles found")
                        return True
                    else:
                        self.print_result(f"NextMuni {agency_tag}", False, "No vehicles found")
                else:
                    self.print_result(f"NextMuni {agency_tag}", False,
                                      f"HTTP {response.status_code}")

            except Exception as e:
                self.print_result(f"NextMuni {agency_tag}", False, f"Exception: {str(e)}")

        print("\n⚠️  NextMuni API may be down or agency parameters have changed")
        return False

    def test_bart_api(self):
        """Test BART API"""
        self.print_header("Testing BART API")

        if self.api_keys['BART'] == 'YOUR_BART_API_KEY':
            self.print_result("BART API", False, "API key not configured in .env file")
            return False

        try:
            url = "https://api.bart.gov/api/etd.aspx"
            params = {
                'cmd': 'etd',
                'orig': 'ALL',
                'key': self.api_keys['BART'],
                'json': 'y'
            }

            start_time = time.time()
            response = self.session.get(url, params=params, timeout=10)
            response_time = (time.time() - start_time) * 1000

            print(f"Response: {response.status_code}")
            print(f"Content length: {len(response.text)} chars")
            print(f"Response time: {response_time:.0f}ms")

            if response.status_code == 200:
                data = response.json()

                # Count stations and departures
                station_count = 0
                departure_count = 0

                if 'root' in data and 'station' in data['root']:
                    stations = data['root']['station']
                    if not isinstance(stations, list):
                        stations = [stations]

                    station_count = len(stations)

                    for station in stations:
                        if 'etd' in station:
                            etds = station['etd']
                            if not isinstance(etds, list):
                                etds = [etds]

                            for etd in etds:
                                if 'estimate' in etd:
                                    estimates = etd['estimate']
                                    if not isinstance(estimates, list):
                                        estimates = [estimates]
                                    departure_count += len(estimates)

                self.print_result("BART API", True,
                                  f"{station_count} stations, {departure_count} departures")

                # Show sample data
                if station_count > 0:
                    sample_station = stations[0]
                    print(f"    Sample station: {sample_station.get('name', 'Unknown')}")

                return True
            else:
                self.print_result("BART API", False, f"HTTP {response.status_code}: {response.text[:100]}")
                return False

        except Exception as e:
            self.print_result("BART API", False, f"Exception: {str(e)}")
            return False

    def test_environment(self):
        """Test environment configuration"""
        self.print_header("Testing Environment Configuration")

        print(f"SF_511_API_KEY: {'✅ SET' if self.api_keys['SF_511'] != 'YOUR_511_API_KEY' else '❌ NOT SET'}")
        print(f"BART_API_KEY: {'✅ SET' if self.api_keys['BART'] != 'YOUR_BART_API_KEY' else '❌ NOT SET'}")

        if self.api_keys['SF_511'] != 'YOUR_511_API_KEY':
            print(f"511 API Key preview: {self.api_keys['SF_511'][:8]}...")

        if self.api_keys['BART'] != 'YOUR_BART_API_KEY':
            print(f"BART API Key preview: {self.api_keys['BART'][:8]}...")

    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 SF Transit API Testing Suite")
        print("=" * 60)

        # Test environment
        self.test_environment()

        # Test each API
        results = {
            '511.org': self.test_511_api(),
            'NextMuni': self.test_nextmuni_api(),
            'BART': self.test_bart_api()
        }

        # Summary
        self.print_header("Test Summary")
        total_tests = len(results)
        passed_tests = sum(results.values())

        for api, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {api}")

        print(f"\nResult: {passed_tests}/{total_tests} tests passed")

        if results['511.org']:
            print("\n🎉 Great! 511.org is working - you should see many vehicles on your map!")
        else:
            print("\n⚠️  511.org failed - check your API key")

        return results


def main():
    """Run the test suite"""
    tester = APITester()
    results = tester.run_all_tests()

    print(f"\n{'=' * 60}")
    print("🔧 Next Steps:")
    if results['511.org']:
        print("1. Restart your Flask server")
        print("2. Check http://127.0.0.1:5000 for vehicles on the map")
        print("3. Use http://127.0.0.1:5000/test for web-based testing")
    else:
        print("1. Check your .env file has the correct SF_511_API_KEY")
        print("2. Verify your API key at https://511.org/open-data")
        print("3. Restart your Flask server after fixing the key")


if __name__ == "__main__":
    main()
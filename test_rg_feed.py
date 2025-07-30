#!/usr/bin/env python3
"""
Test script to examine agency codes in the 511.org RG (Regional) feed.
This will help us understand if vehicles from Golden Gate and AC Transit
appear with their original agency codes or are all marked as 'RG'.
"""

import requests
from google.transit import gtfs_realtime_pb2
from datetime import datetime
import sys

# API configuration
API_KEY = "9f71d12e-31c2-414c-baf8-49337ba9e933"
API_URL = f"http://api.511.org/transit/vehiclepositions?api_key={API_KEY}&agency=RG"

def test_rg_feed():
    """Fetch and analyze the RG feed to see what agency codes are returned."""
    
    print(f"Testing 511.org RG (Regional) Feed")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 80)
    
    try:
        # Make the API request
        print(f"Fetching data from: {API_URL}")
        response = requests.get(API_URL, timeout=30)
        response.raise_for_status()
        
        print(f"Response status: {response.status_code}")
        print(f"Response size: {len(response.content)} bytes")
        print("-" * 80)
        
        # Parse the GTFS-RT feed
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(response.content)
        
        print(f"Feed header timestamp: {datetime.fromtimestamp(feed.header.timestamp)}")
        print(f"Total entities in feed: {len(feed.entity)}")
        print("-" * 80)
        
        # Analyze vehicles and their agency codes
        vehicles_found = 0
        agency_counts = {}
        sample_vehicles = []
        
        for entity in feed.entity:
            if entity.HasField('vehicle'):
                vehicles_found += 1
                vehicle = entity.vehicle
                
                # Extract agency information
                agency = None
                if vehicle.HasField('vehicle') and vehicle.vehicle.HasField('id'):
                    # Sometimes agency is part of the vehicle ID
                    vehicle_id = vehicle.vehicle.id
                    if '_' in vehicle_id:
                        agency = vehicle_id.split('_')[0]
                
                # Check if agency is in the trip descriptor
                if vehicle.HasField('trip') and vehicle.trip.HasField('route_id'):
                    route_id = vehicle.trip.route_id
                    # Some feeds include agency in route_id
                    if not agency and '_' in route_id:
                        agency = route_id.split('_')[0]
                
                # Look for agency in extensions or other fields
                if not agency:
                    agency = "UNKNOWN"
                
                # Count agencies
                agency_counts[agency] = agency_counts.get(agency, 0) + 1
                
                # Collect sample vehicles for detailed output
                if len(sample_vehicles) < 20:
                    sample_info = {
                        'vehicle_id': vehicle.vehicle.id if vehicle.HasField('vehicle') else 'N/A',
                        'agency': agency,
                        'route_id': vehicle.trip.route_id if vehicle.HasField('trip') and vehicle.trip.HasField('route_id') else 'N/A',
                        'trip_id': vehicle.trip.trip_id if vehicle.HasField('trip') and vehicle.trip.HasField('trip_id') else 'N/A',
                        'position': f"({vehicle.position.latitude:.6f}, {vehicle.position.longitude:.6f})" if vehicle.HasField('position') else 'N/A'
                    }
                    sample_vehicles.append(sample_info)
        
        # Print summary
        print(f"\nSUMMARY:")
        print(f"Total vehicles found: {vehicles_found}")
        print(f"\nAgency breakdown:")
        for agency, count in sorted(agency_counts.items()):
            print(f"  {agency}: {count} vehicles")
        
        # Print sample vehicles
        print(f"\nSAMPLE VEHICLES (first {len(sample_vehicles)}):")
        print("-" * 80)
        for i, vehicle in enumerate(sample_vehicles, 1):
            print(f"\nVehicle {i}:")
            print(f"  Vehicle ID: {vehicle['vehicle_id']}")
            print(f"  Agency: {vehicle['agency']}")
            print(f"  Route ID: {vehicle['route_id']}")
            print(f"  Trip ID: {vehicle['trip_id']}")
            print(f"  Position: {vehicle['position']}")
        
        # Additional analysis - check raw protobuf structure
        print("\n" + "-" * 80)
        print("RAW PROTOBUF ANALYSIS (first 3 vehicles):")
        print("-" * 80)
        
        count = 0
        for entity in feed.entity:
            if entity.HasField('vehicle') and count < 3:
                count += 1
                print(f"\nRaw Entity {count}:")
                print(str(entity)[:500] + "..." if len(str(entity)) > 500 else str(entity))
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error parsing feed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_rg_feed()
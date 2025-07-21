#!/usr/bin/env python3
"""
Debug script for 511.org SF API issues
Helps identify protobuf parsing problems
"""

import os
import requests
from dotenv import load_dotenv

# Load environment
load_dotenv()


def debug_511_sf_api():
    """Debug the 511.org SF API endpoint specifically"""

    api_key = os.getenv('SF_511_API_KEY')
    if not api_key or api_key == 'YOUR_511_API_KEY':
        print("❌ SF_511_API_KEY not set in .env file")
        return

    print("🔍 Debugging 511.org SF API...")
    print(f"API Key: {api_key[:10]}...")

    # Test endpoint
    url = "http://api.511.org/transit/vehiclepositions"
    params = {
        'api_key': api_key,
        'agency': 'SF'
    }

    try:
        print(f"\n📡 Testing URL: {url}")
        print(f"📡 Parameters: {params}")

        response = requests.get(url, params=params, timeout=15)

        print(f"\n📊 Response Status: {response.status_code}")
        print(f"📊 Content-Type: {response.headers.get('content-type', 'Unknown')}")
        print(f"📊 Content-Length: {len(response.content)} bytes")

        if response.status_code != 200:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response text: {response.text}")
            return

        # Check if response is protobuf
        content_type = response.headers.get('content-type', '')
        if 'protobuf' not in content_type and 'octet-stream' not in content_type:
            print(f"⚠️  Unexpected content type: {content_type}")
            print(f"Response preview: {response.text[:200]}...")
            return

        # Try to parse as protobuf
        try:
            from google.transit import gtfs_realtime_pb2

            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(response.content)

            print(f"✅ Protobuf parsed successfully!")
            print(f"📊 Feed header timestamp: {feed.header.timestamp}")
            print(f"📊 Total entities: {len(feed.entity)}")

            # Count vehicles
            vehicle_count = 0
            for entity in feed.entity:
                if entity.HasField('vehicle'):
                    vehicle_count += 1

            print(f"📊 Vehicles found: {vehicle_count}")

            if vehicle_count > 0:
                # Show first vehicle example
                for entity in feed.entity:
                    if entity.HasField('vehicle') and entity.vehicle.HasField('position'):
                        vehicle = entity.vehicle
                        position = vehicle.position

                        print(f"\n📍 Sample Vehicle:")
                        print(f"   ID: {vehicle.vehicle.id if vehicle.HasField('vehicle') else 'Unknown'}")
                        print(f"   Route: {vehicle.trip.route_id if vehicle.HasField('trip') else 'Unknown'}")
                        print(f"   Position: {position.latitude}, {position.longitude}")
                        print(f"   Speed: {position.speed if position.HasField('speed') else 'Unknown'}")
                        break
            else:
                print("⚠️  No vehicles found in feed")

        except Exception as parse_error:
            print(f"❌ Protobuf parsing failed: {parse_error}")
            print(f"Error type: {type(parse_error).__name__}")

            # Show raw content preview
            print(f"\n📄 Raw content preview (first 200 bytes):")
            print(response.content[:200])

            # Check if it's XML or JSON instead
            try:
                text_content = response.content.decode('utf-8')
                if text_content.strip().startswith('<'):
                    print("⚠️  Content appears to be XML, not protobuf")
                    print(f"XML preview: {text_content[:300]}...")
                elif text_content.strip().startswith('{'):
                    print("⚠️  Content appears to be JSON, not protobuf")
                    print(f"JSON preview: {text_content[:300]}...")
            except:
                print("❌ Content is not valid UTF-8 text")

    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def test_all_agencies():
    """Test all 511.org agencies to see which work"""

    api_key = os.getenv('SF_511_API_KEY')
    if not api_key or api_key == 'YOUR_511_API_KEY':
        print("❌ SF_511_API_KEY not set in .env file")
        return

    agencies = ['SF', 'GG', 'AC', 'RG']

    print("\n🔍 Testing all 511.org agencies...")

    for agency in agencies:
        print(f"\n--- Testing {agency} ---")

        url = "http://api.511.org/transit/vehiclepositions"
        params = {
            'api_key': api_key,
            'agency': agency
        }

        try:
            response = requests.get(url, params=params, timeout=10)

            if response.status_code != 200:
                print(f"❌ {agency}: HTTP {response.status_code}")
                continue

            # Try protobuf parsing
            try:
                from google.transit import gtfs_realtime_pb2

                feed = gtfs_realtime_pb2.FeedMessage()
                feed.ParseFromString(response.content)

                vehicle_count = sum(1 for entity in feed.entity if entity.HasField('vehicle'))
                print(f"✅ {agency}: {vehicle_count} vehicles, {len(response.content)} bytes")

            except Exception as parse_error:
                print(f"❌ {agency}: Parse error - {parse_error}")

        except Exception as e:
            print(f"❌ {agency}: Request error - {e}")


if __name__ == "__main__":
    print("🚌 511.org SF API Debug Tool")
    print("=" * 50)

    # Debug SF specifically
    debug_511_sf_api()

    # Test all agencies
    test_all_agencies()

    print("\n✅ Debug complete!")
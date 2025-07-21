"""
GTFS data processing models for SF Transit Tracker
"""

import os
import json
import csv
import zipfile
import requests
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict
from io import StringIO, BytesIO
import logging

# Get logger
logger = logging.getLogger(__name__)

# Constants
ROUTE_SHAPES_FILE = 'data/route_shapes.json'


class GTFSProcessor:
    """Handles downloading and processing GTFS static data"""

    def __init__(self):
        self.sfmta_gtfs_url = "https://api.511.org/transit/datafeeds?api_key={}&operator_id=SF"

    def ensure_data_directory(self):
        """Create data directory if it doesn't exist"""
        os.makedirs('data', exist_ok=True)

    def download_sfmta_gtfs(self, api_key: str) -> Optional[bytes]:
        """Download SFMTA GTFS data with multiple fallback sources and better error handling"""

        # Try multiple GTFS sources in order of preference
        gtfs_sources = [
            {
                'name': '511.org API',
                'url': f'https://api.511.org/transit/datafeeds?api_key={api_key}&operator_id=SF',
                'description': '511.org GTFS API - direct ZIP download'
            },
            {
                'name': 'Transit.land',
                'url': 'https://transitland-atlas.s3.amazonaws.com/feeds/f-9q8y-sfmta.zip',
                'description': 'Alternative GTFS source via Transit.land'
            },
            {
                'name': 'SFMTA Direct (HTTP)',
                'url': 'http://gtfs.sfmta.com/transitdata/google_transit.zip',
                'description': 'Official SFMTA GTFS feed via HTTP'
            }
        ]

        for source in gtfs_sources:
            try:
                logger.info(f"Attempting to download GTFS from {source['name']}: {source['url']}")

                # Use longer timeout and better session configuration
                session = requests.Session()
                session.headers.update({
                    'User-Agent': 'SF-Transit-Tracker/1.0 (Python requests)',
                    'Accept': 'application/zip, application/octet-stream, */*',
                    'Accept-Encoding': 'gzip, deflate'
                })

                # Try with different timeout strategies
                timeouts = [30, 60, 120]  # Progressive timeout increases

                for timeout in timeouts:
                    try:
                        logger.info(f"Trying download with {timeout}s timeout...")

                        response = session.get(
                            source['url'],
                            timeout=timeout,
                            stream=True,  # Stream large files
                            verify=True,  # Verify SSL certificates
                            allow_redirects=True
                        )

                        if response.status_code == 200:
                            # Download in chunks to handle large files
                            content = b''
                            total_size = 0

                            for chunk in response.iter_content(chunk_size=8192):
                                if chunk:
                                    content += chunk
                                    total_size += len(chunk)

                                    # Safety limit: 100MB max
                                    if total_size > 100 * 1024 * 1024:
                                        raise Exception("File too large (>100MB)")

                            logger.info(f"Successfully downloaded GTFS: {len(content)} bytes from {source['name']}")

                            # Validate it's actually a ZIP file
                            if content.startswith(b'PK'):  # ZIP file magic number
                                return content
                            else:
                                logger.warning(f"Downloaded file from {source['name']} is not a valid ZIP")
                                break  # Try next source

                        else:
                            logger.warning(f"HTTP {response.status_code} from {source['name']}: {response.text[:200]}")
                            break  # Try next source

                    except (requests.exceptions.Timeout, requests.exceptions.ConnectTimeout) as e:
                        logger.warning(f"Timeout ({timeout}s) downloading from {source['name']}: {e}")
                        continue  # Try with longer timeout

                    except requests.exceptions.RequestException as e:
                        logger.warning(f"Request error from {source['name']}: {e}")
                        break  # Try next source

            except Exception as e:
                logger.error(f"Failed to download from {source['name']}: {e}")
                continue  # Try next source

        # If all sources fail, provide detailed error information
        logger.error("All GTFS download sources failed")
        return None

    def test_gtfs_connectivity(self, api_key: str) -> Dict:
        """Test connectivity to GTFS sources for debugging"""
        test_results = {}

        sources = [
            ('511.org API', f'https://api.511.org/transit/datafeeds?api_key={api_key}&operator_id=SF'),
            ('Transit.land', 'https://transitland-atlas.s3.amazonaws.com/feeds/f-9q8y-sfmta.zip'),
            ('SFMTA Direct (HTTP)', 'http://gtfs.sfmta.com/transitdata/google_transit.zip'),
            ('511.org Status', 'https://api.511.org/transit/datafeeds')
        ]

        for name, url in sources:
            try:
                import time
                start_time = time.time()

                # Use GET for 511.org datafeeds API, HEAD for others
                if '511.org' in url and 'datafeeds' in url and 'api_key' in url:
                    # For 511.org API with API key, use GET but limit content
                    response = requests.get(url, timeout=10, allow_redirects=True, stream=True)

                    # Read just first chunk to verify it works
                    content_sample = b''
                    try:
                        chunk = next(response.iter_content(chunk_size=1024))
                        if chunk:
                            content_sample = chunk
                    except StopIteration:
                        pass

                    # Check if it's a ZIP file
                    is_zip = content_sample.startswith(b'PK')

                    response_time = (time.time() - start_time) * 1000

                    test_results[name] = {
                        'status': response.status_code,
                        'response_time': f"{response_time:.0f}ms",
                        'headers': dict(response.headers),
                        'url': url,
                        'success': response.status_code == 200,
                        'is_zip_file': is_zip,
                        'content_size_estimated': len(content_sample) if content_sample else 0
                    }
                else:
                    # For other sources, use HEAD request
                    response = requests.head(url, timeout=10, allow_redirects=True)
                    response_time = (time.time() - start_time) * 1000

                    test_results[name] = {
                        'status': response.status_code,
                        'response_time': f"{response_time:.0f}ms",
                        'headers': dict(response.headers),
                        'url': url,
                        'success': response.status_code == 200
                    }

            except Exception as e:
                test_results[name] = {
                    'status': 'ERROR',
                    'error': str(e),
                    'url': url,
                    'success': False
                }

        return test_results

    def parse_shapes_for_routes(self, gtfs_zip_content: bytes, route_names: List[str]) -> Dict:
        """Parse shapes.txt from GTFS zip and extract specified routes"""
        try:
            shapes_data = {}

            with zipfile.ZipFile(BytesIO(gtfs_zip_content)) as zf:
                # Read shapes.txt
                if 'shapes.txt' not in zf.namelist():
                    logger.error("shapes.txt not found in GTFS zip")
                    return {}

                with zf.open('shapes.txt') as shapes_file:
                    shapes_csv = csv.DictReader(StringIO(shapes_file.read().decode('utf-8')))

                    # Group points by shape_id
                    shape_points = defaultdict(list)
                    for row in shapes_csv:
                        shape_id = row.get('shape_id', '')
                        # Filter for J and N routes
                        if any(route in shape_id.upper() for route in route_names):
                            shape_points[shape_id].append({
                                'lat': float(row['shape_pt_lat']),
                                'lng': float(row['shape_pt_lon']),
                                'sequence': int(row['shape_pt_sequence'])
                            })

                    # Sort points by sequence and format
                    for shape_id, points in shape_points.items():
                        sorted_points = sorted(points, key=lambda x: x['sequence'])

                        # Determine route name and direction
                        route_name = None
                        direction = 'outbound'  # default

                        if 'J' in shape_id.upper():
                            route_name = 'J'
                        elif 'N' in shape_id.upper():
                            route_name = 'N'

                        if 'I' in shape_id.upper() or 'INBOUND' in shape_id.upper():
                            direction = 'inbound'

                        if route_name:
                            route_key = f"{route_name}-{direction}"
                            shapes_data[route_key] = {
                                'name': f"{route_name}-Church" if route_name == 'J' else f"{route_name}-Judah",
                                'direction': direction,
                                'shape_id': shape_id,
                                'shape': [[p['lat'], p['lng']] for p in sorted_points]
                            }

            return shapes_data

        except Exception as e:
            logger.error(f"Error parsing shapes: {e}")
            return {}

    def save_route_shapes(self, shapes_data: Dict) -> bool:
        """Save processed route shapes to JSON file"""
        try:
            self.ensure_data_directory()

            output_data = {
                'routes': shapes_data,
                'metadata': {
                    'last_updated': datetime.now().isoformat(),
                    'source': 'SFMTA GTFS via 511.org',
                    'routes_included': list(shapes_data.keys())
                }
            }

            with open(ROUTE_SHAPES_FILE, 'w') as f:
                json.dump(output_data, f, indent=2)

            logger.info(f"Saved {len(shapes_data)} route shapes to {ROUTE_SHAPES_FILE}")
            return True

        except Exception as e:
            logger.error(f"Error saving route shapes: {e}")
            return False

    def load_route_shapes(self) -> Dict:
        """Load route shapes from JSON file"""
        try:
            if os.path.exists(ROUTE_SHAPES_FILE):
                with open(ROUTE_SHAPES_FILE, 'r') as f:
                    data = json.load(f)
                    return data
            else:
                logger.warning(f"Route shapes file not found: {ROUTE_SHAPES_FILE}")
                return {}

        except Exception as e:
            logger.error(f"Error loading route shapes: {e}")
            return {}
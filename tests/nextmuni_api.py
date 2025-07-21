import requests
import json

# Base URL for NextBus JSON feed
BASE_URL = 'http://webservices.nextbus.com/service/publicJSONFeed'
# Default agency tag for San Francisco Muni
AGENCY = 'sf-muni'


def fetch(command, params=None):
    """
    Generic function to query the NextBus JSON feed.
    """
    payload = {'command': command}
    if params:
        payload.update(params)
    response = requests.get(BASE_URL, params=payload)
    response.raise_for_status()
    return response.json()


def get_agencies():
    return fetch('agencyList')


def get_routes(agency=AGENCY):
    return fetch('routeList', {'a': agency})


def get_route_config(agency=AGENCY, route=None):
    params = {'a': agency}
    if route:
        params['r'] = route
    return fetch('routeConfig', params)


def get_predictions(agency=AGENCY, route=None, stop=None):
    if not (route and stop):
        raise ValueError("Both route and stop must be provided for predictions")
    return fetch('predictions', {'a': agency, 'r': route, 's': stop})


def get_multi_predictions(agency=AGENCY, stops=None):
    """
    Stops should be a list of strings in the form "route|stopTag".
    """
    params = [('command', 'predictionsForMultiStops'), ('a', agency)]
    for s in (stops or []):
        params.append(('stops', s))
    response = requests.get(BASE_URL, params=params)
    response.raise_for_status()
    return response.json()


def get_vehicle_locations(agency=AGENCY, route=None, since=0):
    params = {'a': agency, 't': since}
    if route:
        params['r'] = route
    return fetch('vehicleLocations', params)


def get_schedule(agency=AGENCY, route=None):
    params = {'a': agency}
    if route:
        params['r'] = route
    return fetch('schedule', params)


def get_messages(agency=AGENCY, routes=None):
    params = {'a': agency}
    # messages can accept multiple 'r' parameters
    payload = {'command': 'messages', 'a': agency}
    if routes:
        # build query string manually
        query = [('command', 'messages'), ('a', agency)]
        for r in routes:
            query.append(('r', r))
        response = requests.get(BASE_URL, params=query)
        response.raise_for_status()
        return response.json()
    return fetch('messages', params)


if __name__ == '__main__':
    # 1. List all agencies
    agencies = get_agencies()
    print("Agencies:\n", json.dumps(agencies, indent=2))

    # 2. List all routes for SF Muni
    routes_resp = get_routes()
    routes = routes_resp.get('route', [])
    print(f"\nFound {len(routes)} routes. Sample:\n", json.dumps(routes[:3], indent=2))

    if routes:
        first_route = routes[0]['tag']
        print(f"\nUsing first route: {first_route}")

        # 3. Get route configuration
        config = get_route_config(route=first_route)
        print(f"\nRoute Config keys: {list(config.keys())}")

        # 4. Pick a couple of stops for predictions
        stops = [s['tag'] for s in config['route'].get('stop', [])[:2]]
        print(f"\nSample stops: {stops}")

        # 5. Predictions for a single stop
        pred = get_predictions(route=first_route, stop=stops[0])
        print(f"\nPredictions for stop {stops[0]}:\n", json.dumps(pred, indent=2))

        # 6. Predictions for multiple stops
        multi = get_multi_predictions(stops=[f"{first_route}|{stops[0]}", f"{first_route}|{stops[1]}"])
        print(f"\nMulti-stop predictions:\n", json.dumps(multi, indent=2))

        # 7. Vehicle locations
        vehicles = get_vehicle_locations(route=first_route)
        print(f"\nVehicle locations:\n", json.dumps(vehicles, indent=2))

        # 8. Schedule
        schedule = get_schedule(route=first_route)
        print(f"\nSchedule:\n", json.dumps(schedule, indent=2))

        # 9. Messages (active alerts)
        messages = get_messages(routes=[first_route])
        print(f"\nMessages for route {first_route}:\n", json.dumps(messages, indent=2))
    else:
        print("No routes found for agency.")
import requests
import logging
from requests.auth import HTTPBasicAuth

from app.core.config import settings

logger = logging.getLogger(__name__)

def get_live_vehicle_locations(traccar_url, username, password):
    """
    Fetches the real-time GPS locations of all vehicles from the Traccar server.
    :param traccar_url: e.g., 'http://demo.traccar.org/api'
    :param username: Traccar account email
    :param password: Password
    :return: Dictionary mapping device_id -> {'lat': latitude, 'lon': longitude}
    """
    try:
        # endpoint for getting the latest positions of all devices
        url = f"{traccar_url}/positions"
        
        response = requests.get(url, auth=HTTPBasicAuth(username, password))
        
        if response.status_code == 200:
            positions = response.json()
            live_locations = {}
            for pos in positions:
                device_id = pos.get("deviceId")
                live_locations[device_id] = {
                    "lat": pos.get("latitude"),
                    "lon": pos.get("longitude"),
                    "speed": pos.get("speed"),       # can be used to detect if stuck in traffic
                    "timestamp": pos.get("fixTime")  # when the GPS ping was recorded
                }
            return live_locations
        else:
            logger.error(f"Traccar API Error: {response.status_code} - {response.text}")
            return {}
            
    except Exception as e:
        logger.error(f"Failed to connect to Traccar: {e}")
        return {}

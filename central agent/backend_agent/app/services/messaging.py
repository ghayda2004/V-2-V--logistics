import logging
import urllib.parse
import requests

from app.core.config import settings

logger = logging.getLogger(__name__)

def generate_google_maps_url(route_coordinates):
    """
    Generates a Google Maps directions URL for a sequence of coordinates.
    :param route_coordinates: List of tuples [(lat, lon), (lat, lon), ...]
    :return: String URL
    """
    if len(route_coordinates) < 2:
        return ""
    
    # Base URL for Google Maps directions
    base_url = "https://www.google.com/maps/dir/"
    
    # Google Maps URL format requires coordinates separated by slashes
    parts = []
    for lat, lon in route_coordinates:
        parts.append(f"{lat},{lon}")
        
    full_url = base_url + "/".join(parts)
    return full_url

def send_telegram_message(chat_id, message_text):
    """
    Sends a message to a driver via Telegram.
    :param chat_id: The Telegram Chat ID of the driver
    :param message_text: The text to send
    """
    bot_token = settings.TELEGRAM_BOT_TOKEN
    if not bot_token:
        logger.warning("Telegram Bot Token is not set. Skipping message send.")
        return False
        
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message_text,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            logger.info(f"Successfully sent message to chat {chat_id}")
            return True
        else:
            logger.error(f"Failed to send Telegram message: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Telegram API Error: {e}")
        return False

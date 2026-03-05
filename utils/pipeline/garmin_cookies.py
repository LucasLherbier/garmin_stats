import pickle
import os

import logging
from garminconnect import Garmin
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_garmin_client(email, password):
    cookies_file = 'garmin_cookies.pkl'
    try:
        # Create a new API client
        client = Garmin(email, password)
        
        # Try to login (this will automatically handle the authentication)
        client.login()
        logger.info("Successfully logged in to Garmin Connect")
        
        return client
    except Exception as e:
        logger.error(f"Failed to login to Garmin Connect: {e}")
        return None

    return client

# Usage
def load_credentials():
    load_dotenv()
    email = os.getenv("USER_EMAIL")
    password = os.getenv("USER_PASSWORD")
    if not email or not password:
        logger.error("USER_EMAIL or USER_PASSWORD environment variables not found.")
        return None, None
    return email, password

def main():
    email, password = load_credentials()
    if email and password:
        return get_garmin_client(email, password)
    return None

import pickle
import os
import json
import logging
from garminconnect import Garmin

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
    script_dir = os.path.dirname(os.path.abspath(__file__))
    creds_path = os.path.join(script_dir, "credentials.json")
    with open(creds_path) as f:
        credentials = json.load(f)
        email = credentials["email"]
        password = credentials["password"]
        return email, password

def main():
    email, password = load_credentials()
    return get_garmin_client(email, password)

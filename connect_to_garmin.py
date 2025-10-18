import json
import logging
from garminconnect import (
    Garmin
)
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load credentials
def load_credentials():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    creds_path = os.path.join(script_dir, "credentials.json")
    with open(creds_path) as f:
        credentials = json.load(f)
        email = credentials["email"]
        password = credentials["password"]
        return email, password

# Connect to Garmin Connect
def connect_to_garmin():
    email, password = load_credentials()
    try:
        client = Garmin(email, password)
        client.login()
        logger.info("Successfully logged in to Garmin Connect.")
        return client
    except Exception as error:
        logger.error(f"Failed to connect to Garmin Connect: {error}")
        return None

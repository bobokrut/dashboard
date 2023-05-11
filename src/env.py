from dotenv import load_dotenv
from os import environ

load_dotenv()

GEOCODING_KEY = environ.get("GEOCODING_KEY")
if not GEOCODING_KEY:
    raise ValueError("GEOCODING_KEY is not set")

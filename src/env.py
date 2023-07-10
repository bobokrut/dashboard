from dotenv import load_dotenv
from os import environ

load_dotenv()

SECRET_KEY = environ.get("SECRET_KEY")
GEOCODING_KEY = environ.get("GEOCODING_KEY")

if not GEOCODING_KEY:
    raise ValueError("GEOCODING_KEY is not set")

if not SECRET_KEY:
    raise ValueError("SECRET_KEY is not set")

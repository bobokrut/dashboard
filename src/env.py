from os import environ

from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = environ.get("SECRET_KEY")
GEOCODING_KEY = environ.get("GEOCODING_KEY")
AZURE_STORAGE_CONNECTION_STRING = environ.get("AZURE_STORAGE_CONNECTION_STRING")
AZURE_STORAGE_CONTAINER = environ.get("AZURE_STORAGE_CONTAINER")
AZURE_FILE_SHARE = environ.get("AZURE_FILE_SHARE")

if not GEOCODING_KEY:
    raise ValueError("GEOCODING_KEY is not set")

if not SECRET_KEY:
    raise ValueError("SECRET_KEY is not set")

if not AZURE_STORAGE_CONNECTION_STRING:
    raise ValueError("AZURE_STORAGE_CONNECTION_STRING is not set")

if not AZURE_STORAGE_CONTAINER:
    raise ValueError("AZURE_STORAGE_CONTAINER is not set")

if not AZURE_FILE_SHARE:
    raise ValueError("AZURE_FILE_SHARE is not set")

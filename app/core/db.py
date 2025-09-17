# app/core/db.py
import os
from google.cloud import firestore_v1
from google.oauth2 import service_account
from dotenv import load_dotenv

# Manually load the .env file at the start
load_dotenv()

# Get the path to our service account key from the environment variable
key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# --- THIS IS THE FIX ---
# Add a check to ensure the environment variable was actually loaded.
if not key_path:
    raise ValueError(
        "FATAL: The 'GOOGLE_APPLICATION_CREDENTIALS' environment variable is not set. "
        "Ensure you have a .env file in the root directory (~/rankforge) with the line: "
        "GOOGLE_APPLICATION_CREDENTIALS=\"service-account.json\""
    )

# Create explicit credentials from our service account file
try:
    credentials = service_account.Credentials.from_service_account_file(key_path)
except FileNotFoundError:
    raise FileNotFoundError(
        f"FATAL: The service account file was not found at the path specified "
        f"by GOOGLE_APPLICATION_CREDENTIALS: '{key_path}'. Ensure the file exists."
    )

# Initialize the Firestore client and FORCE it to use our credentials
db = firestore_v1.AsyncClient(credentials=credentials)


async def get_firestore_client():
    """
    Dependency injector that provides an asynchronous Firestore client.
    """
    yield db
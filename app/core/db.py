import os
from google.cloud import firestore_v1
from google.oauth2 import service_account
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore as firestore_admin

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
    credentials_obj = service_account.Credentials.from_service_account_file(key_path)
except FileNotFoundError:
    raise FileNotFoundError(
        f"FATAL: The service account file was not found at the path specified "
        f"by GOOGLE_APPLICATION_CREDENTIALS: '{key_path}'. Ensure the file exists."
    )

# Initialize the Firestore client and FORCE it to use our credentials
db = firestore_v1.AsyncClient(credentials=credentials_obj)

def initialize_firebase():
    """
    Initialize the Firebase Admin SDK and set up the Firestore client.
    This function should be called once at application startup.
    """
    global db

    # Check if already initialized
    if not firebase_admin._apps:
        # Initialize Firebase Admin SDK with the same credentials
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred, {
            "projectId": "promptforge-c27e8",  # Replace with your Firebase project ID
        })
        print("Firebase Admin SDK initialized successfully.")

    # Ensure the Firestore client is set (already done above, but this confirms it)
    if db is None:
        db = firestore_v1.AsyncClient(credentials=credentials_obj)

# Dependency injector for asynchronous Firestore client
async def get_firestore_client():
    """
    Dependency injector that provides an asynchronous Firestore client.
    """
    yield db

# Expose necessary components
__all__ = ['db', 'initialize_firebase', 'get_firestore_client']
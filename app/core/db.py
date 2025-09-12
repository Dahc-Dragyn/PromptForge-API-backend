import os
from google.cloud import firestore_v1
from google.oauth2 import service_account
from dotenv import load_dotenv

# Manually load the .env file at the start
load_dotenv()

# Get the path to our service account key from the environment variable
key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Create explicit credentials from our service account file
credentials = service_account.Credentials.from_service_account_file(key_path)

# Initialize the Firestore client and FORCE it to use our credentials
db = firestore_v1.AsyncClient(credentials=credentials)


async def get_firestore_client():
    """
    Dependency injector that provides an asynchronous Firestore client.
    """
    yield db
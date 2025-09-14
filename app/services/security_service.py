import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet

# Load environment variables from .env file
load_dotenv()

# --- Core Security Configuration ---
# Get the master encryption key from environment variables.
# This key is used to encrypt all user-provided API keys.
ENCRYPTION_KEY = os.getenv("FERNET_KEY")

if not ENCRYPTION_KEY:
    raise ValueError("FERNET_KEY is not set in the environment. Please generate a key and add it to your .env file.")

# Create a cipher suite instance with the encryption key
cipher_suite = Fernet(ENCRYPTION_KEY.encode())

def encrypt_key(api_key: str) -> str:
    """
    Encrypts a user's API key using the system's master Fernet key.
    Returns the encrypted key as a string.
    """
    if not api_key:
        return ""
    encrypted_key = cipher_suite.encrypt(api_key.encode())
    return encrypted_key.decode()

def decrypt_key(encrypted_key: str) -> str:
    """
    Decrypts a user's API key using the system's master Fernet key.
    Returns the original API key as a string.
    """
    if not encrypted_key:
        return ""
    decrypted_key = cipher_suite.decrypt(encrypted_key.encode())
    return decrypted_key.decode()
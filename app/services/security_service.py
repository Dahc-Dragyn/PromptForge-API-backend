import os
import logging
from dotenv import load_dotenv
from cryptography.fernet import Fernet
import firebase_admin
from firebase_admin import credentials, auth
from fastapi import Depends, HTTPException, status, Path, Request
from fastapi.security import OAuth2PasswordBearer
from typing import Dict

from app.services import firestore_service

# Load environment variables
load_dotenv()

# --- Fernet Encryption Setup ---
ENCRYPTION_KEY = os.getenv("FERNET_KEY")
if not ENCRYPTION_KEY:
    raise ValueError("FERNET_KEY is not set. Please add it to your .env file.")
cipher_suite = Fernet(ENCRYPTION_KEY.encode())

# --- REMOVED REDUNDANT FIREBASE INIT BLOCK ---
# The initialization is now correctly handled in app/main.py via app/core/db.py

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- Authentication Dependencies ---

async def get_current_user(
    request: Request, token: str = Depends(oauth2_scheme)
) -> Dict:
    """
    Dependency to verify Firebase JWT token.
    It returns the decoded token AND attaches it to the request.state for other services to use.
    """
    try:
        decoded_token = auth.verify_id_token(token)
        request.state.user = decoded_token
        return decoded_token
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def require_admin_role(current_user: Dict = Depends(get_current_user)) -> Dict:
    """A dependency that ensures the authenticated user has the 'admin' role."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges are required for this action."
        )
    return current_user

class PromptOwnerOrAdmin:
    """
    A dependency class that checks if the current user is the owner of a
    specific prompt or is an admin.
    """
    async def __call__(
        self,
        prompt_id: str = Path(...),
        current_user: Dict = Depends(get_current_user)
    ):
        if current_user.get("role") == "admin":
            return current_user

        prompt = await firestore_service.get_prompt_by_id(prompt_id)
        if not prompt:
            return current_user

        if prompt.get("owner_id") != current_user.get("uid"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to modify this prompt."
            )
        
        return current_user

# --- Encryption Functions ---
def encrypt_key(api_key: str) -> str:
    """Encrypts a user's API key."""
    if not api_key: return ""
    return cipher_suite.encrypt(api_key.encode()).decode()

def decrypt_key(encrypted_key: str) -> str:
    """Decrypts a user's API key."""
    if not encrypted_key: return ""
    return cipher_suite.decrypt(encrypted_key.encode()).decode()


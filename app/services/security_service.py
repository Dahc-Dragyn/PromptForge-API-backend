# app/services/security_service.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from firebase_admin import auth
from typing import Dict, Any
import os
from cryptography.fernet import Fernet

# Import the global db instance for consistency
from app.core.db import db

# --- Encryption Functions (Unchanged) ---
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    raise RuntimeError("ENCRYPTION_KEY environment variable not set. Application cannot start.")
fernet = Fernet(ENCRYPTION_KEY.encode())

def encrypt_key(api_key: str) -> str:
    """Encrypts an API key using the application's secret key."""
    return fernet.encrypt(api_key.encode()).decode()

def decrypt_key(encrypted_key: str) -> str:
    """Decrypts an API key using the application's secret key."""
    return fernet.decrypt(encrypted_key.encode()).decode()

# --- Authentication Dependency (Unchanged) ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """Dependency to get the current user from a Firebase JWT."""
    try:
        return auth.verify_id_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# --- Authorization Dependencies ---
class PromptOwnerOrAdmin:
    """Dependency class to verify prompt ownership or admin status."""
    async def __call__(self, prompt_id: str, current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        if current_user.get("admin", False):
            return current_user
        prompt_ref = db.collection("prompts").document(prompt_id)
        prompt_doc = await prompt_ref.get()
        if not prompt_doc.exists:
            raise HTTPException(status_code=404, detail="Prompt not found")
        # This correctly checks the nested 'owner.uid' field for Prompts
        owner_uid = prompt_doc.to_dict().get("owner", {}).get("uid")
        if owner_uid != current_user["uid"]:
            raise HTTPException(status_code=403, detail="Not authorized to access this resource")
        return current_user

class TemplateOwnerOrAdmin:
    """Dependency class to verify template ownership or admin status."""
    async def __call__(self, template_id: str, current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        if current_user.get("admin", False):
            return current_user
        
        # This collection name is correct.
        template_ref = db.collection("prompt_templates").document(template_id)
        template_doc = await template_ref.get()

        if not template_doc.exists:
            raise HTTPException(status_code=404, detail="Template not found")
        
        # --- FIX: CHECK THE CORRECT FIELD ---
        # The bug was here. It was checking 'owner.uid' which is used for prompts.
        # Templates use a top-level 'user_id' string field for ownership.
        owner_uid = template_doc.to_dict().get("user_id") 
        # --- END FIX ---

        if owner_uid != current_user["uid"]:
            raise HTTPException(status_code=403, detail="Not authorized to access this resource")
        return current_user
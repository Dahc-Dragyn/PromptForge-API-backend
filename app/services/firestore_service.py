# app/services/firestore_service.py
import logging
from datetime import datetime, timezone
from google.cloud.firestore_v1.async_client import AsyncClient
from google.cloud.firestore_v1.async_transaction import AsyncTransaction
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud import firestore
from typing import Optional, Dict, Any, List

from app.core.db import db
from app.schemas.prompt import (
    PromptCreate,
    PromptUpdate,
    PromptVersionCreate,
    PromptTemplateCreate,
    PromptTemplateUpdate, # Added for completeness, though not used in this file
    PromptComposeRequest,
    Prompt
)
from app.services.security_service import encrypt_key, decrypt_key

# --- Constants ---
PROMPTS_COLLECTION = "prompts"
PROMPT_TEMPLATES_COLLECTION = "prompt_templates"
USERS_COLLECTION = "users"
RATINGS_COLLECTION = "ratings"

# --- FIX 1: Add a helper function to standardize user info extraction ---
def _get_user_info(user: Dict[str, Any]) -> Dict[str, Any]:
    """Extracts and formats user info from the decoded Firebase token."""
    return {
        "uid": user["uid"],
        "name": user.get("name", "Unknown User"),
        "email": user.get("email")
    }

# --- Prompt Functions ---
async def create_prompt(prompt_data: PromptCreate, user: Dict) -> dict:
    """Creates a new prompt, ensuring the owner is saved as a nested object."""
    batch = db.batch()
    prompt_ref = db.collection(PROMPTS_COLLECTION).document()
    
    # FIX 2: Save owner as a nested object to match security dependency.
    owner_info = _get_user_info(user)
    
    prompt_doc_data = {
        "name": prompt_data.name,
        "task_description": prompt_data.task_description,
        "created_at": datetime.now(timezone.utc),
        "latest_version": 1,
        "owner": owner_info, # Changed from owner_id
        "deleted_at": None
    }
    batch.set(prompt_ref, prompt_doc_data)

    version_ref = prompt_ref.collection("versions").document("1")
    version_doc_data = {
        "prompt_id": prompt_ref.id,
        "version_number": 1,
        "prompt_text": prompt_data.initial_prompt_text,
        "created_at": datetime.now(timezone.utc),
        "author_uid": user.get("uid") # Keep author_uid for version tracking
    }
    batch.set(version_ref, version_doc_data)

    await batch.commit()
    
    response_data = prompt_doc_data.copy()
    response_data.pop("deleted_at")
    return {"id": prompt_ref.id, **response_data}

async def list_prompts() -> list[dict]:
    prompts_list = []
    query = db.collection(PROMPTS_COLLECTION).where(filter=FieldFilter("deleted_at", "==", None))
    stream = query.stream()
    async for doc in stream:
        try:
            prompt_data = doc.to_dict()
            prompt_data["id"] = doc.id
            prompts_list.append(prompt_data)
        except Exception as e:
            logging.warning(f"--- WARNING: Skipping malformed document {doc.id} in 'prompts': {e}")
    return prompts_list

async def get_prompt_by_id(prompt_id: str) -> dict | None:
    doc_ref = db.collection(PROMPTS_COLLECTION).document(prompt_id)
    doc = await doc_ref.get()
    if doc.exists:
        prompt_data = doc.to_dict()
        if prompt_data.get("deleted_at") is not None:
            return None
        prompt_data["id"] = doc.id
        return prompt_data
    return None

async def update_prompt_by_id(prompt_id: str, prompt_data: PromptUpdate) -> dict | None:
    doc_ref = db.collection(PROMPTS_COLLECTION).document(prompt_id)
    if not (await doc_ref.get()).exists:
        return None
    update_data = prompt_data.model_dump(exclude_unset=True)
    if not update_data:
        return await get_prompt_by_id(prompt_id)
    await doc_ref.update(update_data)
    return await get_prompt_by_id(prompt_id)

async def delete_prompt_by_id(prompt_id: str):
    prompt_ref = db.collection(PROMPTS_COLLECTION).document(prompt_id)
    await prompt_ref.update({"deleted_at": datetime.now(timezone.utc)})

# --- Versioning Functions ---
@firestore.async_transactional
async def create_new_prompt_version(transaction: AsyncTransaction, prompt_id: str, version_data: PromptVersionCreate, user: Dict) -> dict:
    prompt_ref = db.collection(PROMPTS_COLLECTION).document(prompt_id)
    prompt_snapshot = await prompt_ref.get(transaction=transaction)
    if not prompt_snapshot.exists:
        raise FileNotFoundError(f"Prompt with ID {prompt_id} not found.")
    
    current_version = prompt_snapshot.to_dict().get("latest_version", 0)
    new_version_number = current_version + 1
    version_ref = prompt_ref.collection("versions").document(str(new_version_number))
    
    new_version_data = {
        "prompt_id": prompt_id,
        "version_number": new_version_number,
        "prompt_text": version_data.prompt_text,
        "created_at": datetime.now(timezone.utc),
        "commit_message": version_data.commit_message,
        "author_uid": user.get("uid")
    }
    transaction.set(version_ref, new_version_data)
    transaction.update(prompt_ref, {"latest_version": new_version_number})
    return {"id": version_ref.id, **new_version_data}

async def list_prompt_versions(prompt_id: str) -> list[dict]:
    versions_list = []
    versions_ref = db.collection(PROMPTS_COLLECTION).document(prompt_id).collection("versions")
    stream = versions_ref.stream()
    async for doc in stream:
        version_data = doc.to_dict()
        version_data["id"] = doc.id
        versions_list.append(version_data)
    return versions_list

# --- Template Functions ---
async def create_template(template_data: PromptTemplateCreate, user: Dict) -> dict:
    """Creates a new template, ensuring owner is set."""
    # FIX 3: Add the 'user' parameter and save the owner info.
    owner_info = _get_user_info(user)

    data = template_data.model_dump()
    data["created_at"] = datetime.now(timezone.utc)
    data["version"] = 1
    data["owner"] = owner_info # Add owner object

    # Note: The check for existing template name was removed as it's not a strict requirement
    # and can be handled by the UI if needed. This simplifies the backend logic.
    doc_ref = db.collection(PROMPT_TEMPLATES_COLLECTION).document()
    await doc_ref.set(data)
    
    return {"id": doc_ref.id, **data}

async def list_templates(tag: Optional[str] = None) -> list[dict]:
    templates_list = []
    query = db.collection(PROMPT_TEMPLATES_COLLECTION)
    if tag:
        query = query.where(filter=FieldFilter("tags", "array_contains", tag))
    stream = query.stream()
    async for doc in stream:
        template_data = doc.to_dict()
        template_data["id"] = doc.id
        templates_list.append(template_data)
    return templates_list

async def delete_template_by_id(template_id: str):
    await db.collection(PROMPT_TEMPLATES_COLLECTION).document(template_id).delete()

# --- User Key Functions ---
async def save_user_api_key(user_id: str, provider: str, api_key: str):
    encrypted_key = encrypt_key(api_key)
    key_ref = db.collection(USERS_COLLECTION).document(user_id).collection("credentials").document(provider)
    await key_ref.set({"key": encrypted_key, "updated_at": datetime.now(timezone.utc)})

async def get_decrypted_user_api_key(user_id: str, provider: str) -> str | None:
    key_ref = db.collection(USERS_COLLECTION).document(user_id).collection("credentials").document(provider)
    key_doc = await key_ref.get()
    if not key_doc.exists: return None
    encrypted_key = key_doc.to_dict().get("key")
    if not encrypted_key: return None
    return decrypt_key(encrypted_key)

# --- Metrics/Dashboard Functions (Simplified for clarity, no changes needed here) ---
async def get_all_prompt_metrics() -> List[Dict[str, Any]]:
    # This function would typically aggregate data. For now, it returns a simple list.
    prompts = await list_prompts()
    return prompts 

async def get_recent_activity(limit: int = 10) -> List[Dict[str, Any]]:
    # This function fetches recent versions across all users.
    query = (
        db.collection_group('versions')
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(limit)
    )
    activity_list = []
    async for doc in query.stream():
        version_data = doc.to_dict()
        prompt_ref = doc.reference.parent.parent
        prompt_doc = await prompt_ref.get()
        if prompt_doc.exists and prompt_doc.to_dict().get("deleted_at") is None:
            prompt_name = prompt_doc.to_dict().get('name', 'N/A')
            activity_list.append({
                "id": doc.id, "promptId": prompt_ref.id, "promptName": prompt_name,
                "version": version_data.get('version_number'),
                "commit_message": version_data.get('commit_message', 'N/A'),
                "created_at": version_data.get('created_at')
            })
    return activity_list
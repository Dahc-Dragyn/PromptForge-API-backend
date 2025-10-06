# app/services/firestore_service.py
import logging
from datetime import datetime, timezone
from google.cloud.firestore_v1.async_client import AsyncClient
from google.cloud.firestore_v1.async_transaction import AsyncTransaction
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud import firestore
from typing import Optional, Dict, Any, List
import asyncio

from app.core.db import db
from app.schemas.prompt import (
    PromptCreate,
    PromptUpdate,
    PromptVersionCreate,
    PromptTemplateCreate,
    PromptTemplateUpdate,
    PromptComposeRequest,
    Prompt
)
from app.services.security_service import encrypt_key, decrypt_key

# --- Constants ---
PROMPTS_COLLECTION = "prompts"
PROMPT_TEMPLATES_COLLECTION = "prompt_templates"
USERS_COLLECTION = "users"
RATINGS_COLLECTION = "ratings"

# --- Helper Functions ---
def _get_user_info(user: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "uid": user["uid"],
        "name": user.get("name", "Unknown User"),
        "email": user.get("email")
    }

def _serialize_datetimes(data: Dict[str, Any]) -> Dict[str, Any]:
    if data is None:
        return None
    for key, value in data.items():
        if isinstance(value, datetime):
            data[key] = value.isoformat()
    return data

# --- Prompt and Template Functions ---
async def create_prompt(prompt_data: PromptCreate, user: Dict) -> dict:
    batch = db.batch()
    prompt_ref = db.collection(PROMPTS_COLLECTION).document()
    owner_info = _get_user_info(user)
    creation_time = datetime.now(timezone.utc)
    
    prompt_doc_data = {
        "name": prompt_data.name,
        "task_description": prompt_data.task_description,
        "created_at": creation_time,
        "latest_version": 1,
        "owner": owner_info,
        "deleted_at": None,
        "average_rating": 0,
        "rating_count": 0
    }
    batch.set(prompt_ref, prompt_doc_data)

    version_ref = prompt_ref.collection("versions").document("1")
    version_doc_data = {
        "prompt_id": prompt_ref.id,
        "version_number": 1,
        "prompt_text": prompt_data.initial_prompt_text,
        "created_at": creation_time,
        "author_uid": user.get("uid")
    }
    batch.set(version_ref, version_doc_data)

    await batch.commit()
    
    response_data = prompt_doc_data.copy()
    response_data.pop("deleted_at")
    
    return _serialize_datetimes({"id": prompt_ref.id, **response_data})

async def list_prompts() -> list[dict]:
    prompts_list = []
    query = db.collection(PROMPTS_COLLECTION).where(filter=FieldFilter("deleted_at", "==", None))
    stream = query.stream()
    async for doc in stream:
        try:
            prompt_data = doc.to_dict()
            prompt_data["id"] = doc.id
            
            # Defensive check to ensure rating fields always exist.
            if "average_rating" not in prompt_data:
                prompt_data["average_rating"] = 0.0
            if "rating_count" not in prompt_data:
                prompt_data["rating_count"] = 0
                
            prompts_list.append(_serialize_datetimes(prompt_data))
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
        return _serialize_datetimes(prompt_data)
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
        "prompt_id": prompt_id, "version_number": new_version_number,
        "prompt_text": version_data.prompt_text, "created_at": datetime.now(timezone.utc),
        "commit_message": version_data.commit_message, "author_uid": user.get("uid")
    }
    transaction.set(version_ref, new_version_data)
    transaction.update(prompt_ref, {"latest_version": new_version_number})
    return _serialize_datetimes({"id": version_ref.id, **new_version_data})

async def list_prompt_versions(prompt_id: str) -> list[dict]:
    versions_list = []
    versions_ref = db.collection(PROMPTS_COLLECTION).document(prompt_id).collection("versions")
    stream = versions_ref.stream()
    async for doc in stream:
        version_data = doc.to_dict()
        version_data["id"] = doc.id
        versions_list.append(_serialize_datetimes(version_data))
    return versions_list

async def create_template(template_data: PromptTemplateCreate, user: Dict) -> dict:
    owner_info = _get_user_info(user)
    data = template_data.model_dump()
    data["created_at"] = datetime.now(timezone.utc)
    data["version"] = 1
    data["owner"] = owner_info
    doc_ref = db.collection(PROMPT_TEMPLATES_COLLECTION).document()
    await doc_ref.set(data)
    return _serialize_datetimes({"id": doc_ref.id, **data})

async def list_templates(tag: Optional[str] = None) -> list[dict]:
    templates_list = []
    query = db.collection(PROMPT_TEMPLATES_COLLECTION)
    if tag:
        query = query.where(filter=FieldFilter("tags", "array_contains", tag))
    stream = query.stream()
    async for doc in stream:
        template_data = doc.to_dict()
        template_data["id"] = doc.id
        templates_list.append(_serialize_datetimes(template_data))
    return templates_list

async def list_templates_by_tags(tags: list[str]) -> list[dict]:
    templates_list = []
    if not tags:
        return templates_list
    query = db.collection(PROMPT_TEMPLATES_COLLECTION).where(filter=FieldFilter("tags", "array_contains_any", tags))
    async for doc in query.stream():
        template_data = doc.to_dict()
        template_data["id"] = doc.id
        templates_list.append(_serialize_datetimes(template_data))
    return templates_list

async def delete_template_by_id(template_id: str):
    await db.collection(PROMPT_TEMPLATES_COLLECTION).document(template_id).delete()

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

async def get_all_prompt_metrics() -> List[Dict[str, Any]]:
    prompts = await list_prompts()
    return prompts

async def get_recent_activity(limit: int = 10) -> List[Dict[str, Any]]:
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
            activity_item = {
                "id": doc.id, "promptId": prompt_ref.id, "promptName": prompt_name,
                "version": version_data.get('version_number'),
                "commit_message": version_data.get('commit_message', 'N/A'),
                "created_at": version_data.get('created_at')
            }
            activity_list.append(_serialize_datetimes(activity_item))
    return activity_list

@firestore.async_transactional
async def create_or_update_rating(
    transaction: AsyncTransaction,
    prompt_id: str,
    version_number: int,
    rating: int,
    user_id: str
):
    prompt_ref = db.collection(PROMPTS_COLLECTION).document(prompt_id)
    prompt_snapshot = await prompt_ref.get(transaction=transaction)

    if not prompt_snapshot.exists:
        raise FileNotFoundError(f"Prompt with ID {prompt_id} not found.")

    rating_id = f"{prompt_id}_v{version_number}_{user_id}"
    rating_ref = db.collection(RATINGS_COLLECTION).document(rating_id)

    transaction.set(rating_ref, {
        "prompt_id": prompt_id,
        "version_number": version_number,
        "user_id": user_id,
        "rating": rating,
        "created_at": datetime.now(timezone.utc)
    })

    prompt_data = prompt_snapshot.to_dict()
    old_rating_count = prompt_data.get("rating_count", 0)
    old_avg_rating = prompt_data.get("average_rating", 0.0)
    
    new_rating_count = old_rating_count + 1
    new_avg_rating = ((old_avg_rating * old_rating_count) + rating) / new_rating_count

    transaction.update(prompt_ref, {
        "rating_count": new_rating_count,
        "average_rating": new_avg_rating
    })
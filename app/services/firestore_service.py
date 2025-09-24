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
    PromptComposeRequest,
    Prompt
)
from app.services.security_service import encrypt_key, decrypt_key

# --- Constants ---
PROMPTS_COLLECTION = "prompts"
PROMPT_TEMPLATES_COLLECTION = "prompt_templates"
USERS_COLLECTION = "users"
RATINGS_COLLECTION = "ratings"

# --- All existing, working functions are preserved ---
async def create_prompt(prompt_data: PromptCreate, user: Dict) -> dict:
    batch = db.batch()
    prompt_ref = db.collection(PROMPTS_COLLECTION).document()
    prompt_doc_data = {
        "name": prompt_data.name, "task_description": prompt_data.task_description,
        "created_at": datetime.now(timezone.utc), "latest_version": 1,
        "owner_id": user.get("uid"), "deleted_at": None
    }
    batch.set(prompt_ref, prompt_doc_data)
    version_ref = prompt_ref.collection("versions").document("1")
    version_doc_data = {
        "prompt_id": prompt_ref.id, "version_number": 1,
        "prompt_text": prompt_data.initial_prompt_text,
        "created_at": datetime.now(timezone.utc), "author_uid": user.get("uid")
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
            Prompt.model_validate(prompt_data)
            prompts_list.append(prompt_data)
        except Exception as e:
            logging.warning(f"--- WARNING: Skipping malformed document in 'prompts' collection ---")
            logging.warning(f"Document ID: {doc.id}")
            logging.warning(f"Error: {e}")
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

async def get_prompts_summary() -> list[dict]:
    prompts = await list_prompts()
    summary_list = []
    for prompt in prompts:
        summary_list.append({
            **prompt,
            "version_count": prompt.get("latest_version", 0),
            "average_rating": prompt.get("average_rating", 0.0),
            "rating_count": prompt.get("rating_count", 0)
        })
    return summary_list

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

async def create_template(template_data: PromptTemplateCreate) -> dict:
    existing_template_query = db.collection(PROMPT_TEMPLATES_COLLECTION).where(filter=FieldFilter("name", "==", template_data.name)).limit(1)
    docs = [doc async for doc in existing_template_query.stream()]
    if docs:
        raise ValueError("A template with this name already exists.")
    data = template_data.model_dump()
    data["created_at"] = datetime.now(timezone.utc)
    data["version"] = 1
    _, doc_ref = await db.collection(PROMPT_TEMPLATES_COLLECTION).add(data)
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

async def compose_prompt_from_tags(request: PromptComposeRequest) -> dict:
    ordered_tags = {"persona": request.persona, "task": request.task, "style": request.style, "output_format": request.output_format, "domain": request.domain, "language": request.language}
    prompt_pieces, source_templates, used_template_ids = [], [], set()
    for _, tag_name in ordered_tags.items():
        if tag_name:
            query = db.collection(PROMPT_TEMPLATES_COLLECTION).where(filter=FieldFilter("tags", "array_contains", tag_name)).limit(5)
            async for doc in query.stream():
                if doc.id not in used_template_ids:
                    template_data = doc.to_dict()
                    prompt_pieces.append(template_data.get("content", ""))
                    source_templates.append(template_data.get("name", "Unknown"))
                    used_template_ids.add(doc.id)
                    break
    return {"composed_prompt": "\n\n".join(prompt_pieces), "source_templates": source_templates}

async def list_templates_by_tags(tags: list[str]) -> list[dict]:
    templates_list = []
    query = db.collection(PROMPT_TEMPLATES_COLLECTION).where(filter=FieldFilter("tags", "array_contains_any", tags))
    async for doc in query.stream():
        template_data = doc.to_dict()
        template_data["id"] = doc.id
        templates_list.append(template_data)
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

async def get_prompt_summary_with_ratings(user_id: str) -> List[Dict[str, Any]]:
    prompts_ref = db.collection(PROMPTS_COLLECTION).where(filter=FieldFilter("owner_id", "==", user_id)).where(filter=FieldFilter("deleted_at", "==", None))
    prompts_stream = prompts_ref.stream()
    
    ratings_ref = db.collection(RATINGS_COLLECTION).where(filter=FieldFilter("user_id", "==", user_id))
    ratings_stream = ratings_ref.stream()

    ratings_by_prompt = {}
    async for rating_doc in ratings_stream:
        rating_data = rating_doc.to_dict()
        prompt_id = rating_data.get('prompt_id')
        if prompt_id not in ratings_by_prompt:
            ratings_by_prompt[prompt_id] = []
        ratings_by_prompt[prompt_id].append(rating_data['rating'])

    summaries = []
    async for prompt_doc in prompts_stream:
        prompt_data = prompt_doc.to_dict()
        prompt_id = prompt_doc.id
        
        ratings = ratings_by_prompt.get(prompt_id, [])
        avg_rating = sum(ratings) / len(ratings) if ratings else 0.0
        
        summary = {
            "id": prompt_id,
            "name": prompt_data.get("name"),
            # FIX: Add the missing description field to match the Pydantic schema
            "description": prompt_data.get("task_description", ""), 
            "average_rating": avg_rating,
            "rating_count": len(ratings)
        }
        summaries.append(summary)
        
    return summaries

async def get_recent_activity(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Retrieves the most recently created prompt versions for a specific user,
    leveraging the Firestore composite index for efficient sorting.
    """
    query = (
        db.collection_group('versions')
        .where(filter=FieldFilter("author_uid", "==", user_id))
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(limit)
    )
    activity_list = []
    
    async for doc in query.stream():
        version_data = doc.to_dict()
        prompt_ref = doc.reference.parent.parent
        
        prompt_doc = await prompt_ref.get()
        if not prompt_doc.exists or prompt_doc.to_dict().get("deleted_at") is not None:
            continue
        
        prompt_name = prompt_doc.to_dict().get('name', 'N/A')

        activity_item = {
            "id": doc.id,
            "promptId": prompt_ref.id,
            "promptName": prompt_name,
            "version": version_data.get('version_number'),
            "commit_message": version_data.get('commit_message', 'No commit message.'),
            "created_at": version_data.get('created_at')
        }
        activity_list.append(activity_item)
    return activity_list

async def create_rating_for_version(user_id: str, prompt_id: str, version_number: int, rating_value: int) -> str:
    ratings_collection = db.collection(RATINGS_COLLECTION)
    _, new_rating_ref = await ratings_collection.add({
        'user_id': user_id,
        'prompt_id': prompt_id,
        'version_number': version_number,
        'rating': rating_value,
        'created_at': datetime.now(timezone.utc)
    })
    return new_rating_ref.id
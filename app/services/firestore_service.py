from datetime import datetime, timezone
from google.cloud.firestore_v1.async_client import AsyncClient
from google.cloud.firestore_v1.async_transaction import AsyncTransaction
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud import firestore
from typing import Optional
import traceback # Import traceback to print detailed errors

from app.core.db import db
from app.schemas.prompt import (
    PromptCreate,
    PromptUpdate,
    PromptVersionCreate,
    PromptTemplateCreate,
    PromptComposeRequest,
    Prompt # Import the main Prompt schema for validation
)

# --- Constants ---
PROMPTS_COLLECTION = "prompts"
PROMPT_TEMPLATES_COLLECTION = "prompt_templates"


# --- Prompt Service Functions ---

async def create_prompt(prompt_data: PromptCreate) -> dict:
    """Creates a new prompt and its first version atomically."""
    batch = db.batch()
    prompt_ref = db.collection(PROMPTS_COLLECTION).document()
    prompt_doc_data = {
        "name": prompt_data.name,
        "task_description": prompt_data.task_description,
        "created_at": datetime.now(timezone.utc),
        "latest_version": 1
    }
    batch.set(prompt_ref, prompt_doc_data)
    version_ref = prompt_ref.collection("versions").document("1")
    version_doc_data = {
        "prompt_id": prompt_ref.id,
        "version_number": 1,
        "prompt_text": prompt_data.initial_prompt_text,
        "created_at": datetime.now(timezone.utc)
    }
    batch.set(version_ref, version_doc_data)
    await batch.commit()
    return {"id": prompt_ref.id, **prompt_doc_data}

async def list_prompts() -> list[dict]:
    """
    Retrieves all prompt documents, safely skipping any malformed ones.
    """
    prompts_list = []
    stream = db.collection(PROMPTS_COLLECTION).stream()
    async for doc in stream:
        try:
            prompt_data = doc.to_dict()
            prompt_data["id"] = doc.id
            # Validate data against the Pydantic model before adding it
            Prompt.model_validate(prompt_data)
            prompts_list.append(prompt_data)
        except Exception as e:
            # If validation fails or any other error occurs, log it and continue
            print(f"--- WARNING: Skipping malformed document in 'prompts' collection ---")
            print(f"Document ID: {doc.id}")
            print(f"Document Data: {doc.to_dict()}")
            print(f"Error: {e}")
            print("-" * 60)
            
    return prompts_list

async def get_prompt_by_id(prompt_id: str) -> dict | None:
    """Retrieves a single prompt document by its ID."""
    doc_ref = db.collection(PROMPTS_COLLECTION).document(prompt_id)
    doc = await doc_ref.get()
    if doc.exists:
        prompt_data = doc.to_dict()
        prompt_data["id"] = doc.id
        return prompt_data
    return None

async def update_prompt_by_id(prompt_id: str, prompt_data: PromptUpdate) -> dict | None:
    """Updates a prompt document by its ID."""
    doc_ref = db.collection(PROMPTS_COLLECTION).document(prompt_id)
    if not (await doc_ref.get()).exists:
        return None
    update_data = prompt_data.model_dump(exclude_unset=True)
    if not update_data:
        return await get_prompt_by_id(prompt_id)
    await doc_ref.update(update_data)
    return await get_prompt_by_id(prompt_id)

async def delete_prompt_by_id(prompt_id: str):
    """Deletes a prompt document by its ID."""
    await db.collection(PROMPTS_COLLECTION).document(prompt_id).delete()

# --- Versioning Service Functions ---

async def list_prompt_versions(prompt_id: str) -> list[dict]:
    """Retrieves all versions for a given prompt."""
    versions_list = []
    versions_ref = db.collection(PROMPTS_COLLECTION).document(prompt_id).collection("versions")
    stream = versions_ref.order_by("version_number", direction="DESCENDING").stream()
    async for doc in stream:
        version_data = doc.to_dict()
        version_data["id"] = doc.id
        versions_list.append(version_data)
    return versions_list

@firestore.async_transactional
async def create_new_prompt_version(transaction: AsyncTransaction, prompt_id: str, version_data: PromptVersionCreate) -> dict:
    """Creates a new version for a prompt atomically."""
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
        "commit_message": version_data.commit_message
    }
    transaction.set(version_ref, new_version_data)
    transaction.update(prompt_ref, {"latest_version": new_version_number})
    return {"id": version_ref.id, **new_version_data}

# --- Template Service Functions ---

async def create_template(template_data: PromptTemplateCreate) -> dict:
    """Creates a new prompt template after checking for name uniqueness."""
    existing_template_query = db.collection(PROMPT_TEMPLATES_COLLECTION).where(
        filter=FieldFilter("name", "==", template_data.name)
    ).limit(1)

    docs = [doc async for doc in existing_template_query.stream()]
    if docs:
        raise ValueError("A template with this name already exists.")

    data = template_data.model_dump()
    data["created_at"] = datetime.now(timezone.utc)
    data["version"] = 1

    update_time, doc_ref = await db.collection(PROMPT_TEMPLATES_COLLECTION).add(data)
    return {"id": doc_ref.id, **data}

async def list_templates(tag: Optional[str] = None) -> list[dict]:
    """Retrieves all prompt templates, optionally filtering by a tag."""
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
    """Finds unique templates matching the requested tags and composes them."""
    ordered_tags = {
        "persona": request.persona,
        "task": request.task,
        "style": request.style,
        "output_format": request.output_format,
        "domain": request.domain,
        "language": request.language
    }

    prompt_pieces = []
    source_templates = []
    used_template_ids = set()

    for category, tag_name in ordered_tags.items():
        if tag_name:
            query = db.collection(PROMPT_TEMPLATES_COLLECTION).where(
                filter=FieldFilter("tags", "array_contains", tag_name)
            ).limit(5)

            stream = query.stream()
            async for doc in stream:
                if doc.id not in used_template_ids:
                    template_data = doc.to_dict()
                    prompt_pieces.append(template_data.get("content", ""))
                    source_templates.append(template_data.get("name", "Unknown"))
                    used_template_ids.add(doc.id)
                    break

    composed_prompt = "\n\n".join(prompt_pieces)

    return {
        "composed_prompt": composed_prompt,
        "source_templates": source_templates
    }

async def list_templates_by_tags(tags: list[str]) -> list[dict]:
    """Retrieves all prompt templates that contain ANY of the given tags."""
    templates_list = []
    # Firestore's 'array-contains-any' is perfect for this OR logic
    query = db.collection(PROMPT_TEMPLATES_COLLECTION).where(
        filter=FieldFilter("tags", "array_contains_any", tags)
    )

    stream = query.stream()
    async for doc in stream:
        template_data = doc.to_dict()
        template_data["id"] = doc.id
        templates_list.append(template_data)

    return templates_list

async def delete_template_by_id(template_id: str):
    """Deletes a template document by its ID."""
    # This is idempotent, it won't error if the doc is already gone
    await db.collection(PROMPT_TEMPLATES_COLLECTION).document(template_id).delete()
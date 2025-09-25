# app/routers/templates.py
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict
from app.services import firestore_service, security_service
from app.schemas.prompt import PromptTemplate, PromptTemplateCreate, PromptTemplateUpdate

# FIX: The 'prefix' argument is removed.
router = APIRouter(
    tags=["Templates"],
)

# --- FIX 1: Create an instance of our dependency to reuse ---
template_owner_or_admin_dependency = security_service.TemplateOwnerOrAdmin()

@router.post("/", response_model=PromptTemplate, status_code=201)
async def create_new_template(
    template_data: PromptTemplateCreate,
    current_user: Dict = Depends(security_service.get_current_user)
):
    """(SECURE) Creates a new prompt template."""
    created_template = await firestore_service.create_template(template_data, user=current_user)
    return created_template

@router.get("/", response_model=List[PromptTemplate])
async def get_all_templates():
    """(PUBLIC) Retrieves all prompt templates."""
    templates = await firestore_service.list_templates()
    return templates

@router.get("/{template_id}", response_model=PromptTemplate)
async def get_single_template(template_id: str):
    """(PUBLIC) Retrieves a single prompt template by its ID."""
    template = await firestore_service.get_template_by_id(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template

# --- FIX 2: Protect the UPDATE endpoint ---
@router.patch("/{template_id}", response_model=PromptTemplate)
async def update_single_template(
    template_id: str,
    template_update: PromptTemplateUpdate,
    _ = Depends(template_owner_or_admin_dependency) # Checks for owner/admin
):
    """(SECURE) Updates a single prompt template. Requires ownership or admin role."""
    updated_template = await firestore_service.update_template_by_id(template_id, template_update.dict(exclude_unset=True))
    if not updated_template:
        raise HTTPException(status_code=404, detail="Template not found")
    return updated_template

# --- FIX 3: Protect the DELETE endpoint ---
@router.delete("/{template_id}", status_code=204)
async def delete_single_template(
    template_id: str,
    _ = Depends(template_owner_or_admin_dependency) # Checks for owner/admin
):
    """(SECURE) Deletes a single prompt template. Requires ownership or admin role."""
    await firestore_service.delete_template_by_id(template_id)
    return {"message": "Template deleted successfully"}
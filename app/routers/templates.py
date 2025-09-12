from fastapi import APIRouter, Depends, HTTPException, Response
from google.cloud.firestore_v1.async_client import AsyncClient
from typing import List, Optional

from app.core.db import get_firestore_client
from app.schemas.prompt import (
    PromptTemplate, 
    PromptTemplateCreate,
    PromptComposeRequest,
    PromptComposeResponse,
    TemplateGenerateRequest,
    RecommendRequest,
    RecommendResponse
)
from app.services import firestore_service, llm_service

router = APIRouter(
    prefix="/templates",
    tags=["Templates"],
)

@router.post("/", response_model=PromptTemplate, status_code=201)
async def create_new_template(template: PromptTemplateCreate):
    """Create a new prompt template in the library."""
    try:
        created_template = await firestore_service.create_template(template)
        return created_template
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

@router.get("/", response_model=List[PromptTemplate])
async def get_all_templates(tag: Optional[str] = None):
    """Retrieve all prompt templates, optionally filtering by a tag."""
    templates = await firestore_service.list_templates(tag)
    return templates

@router.post("/compose", response_model=PromptComposeResponse)
async def compose_prompt_from_template_tags(request: PromptComposeRequest):
    """Dynamically composes a new prompt from templates based on tags."""
    composed_data = await firestore_service.compose_prompt_from_tags(request)
    if not composed_data["composed_prompt"]:
        return PromptComposeResponse(composed_prompt="Could not compose a prompt from the given tags.", source_templates=[])
    return PromptComposeResponse(**composed_data)

@router.post("/generate", response_model=PromptTemplate, status_code=201)
async def generate_new_template_with_ai(request: TemplateGenerateRequest):
    """Uses an LLM to generate a new prompt template and saves it to the library."""
    try:
        created_template = await llm_service.generate_and_store_template(request)
        return created_template
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate and store template: {str(e)}")

@router.post("/recommend", response_model=RecommendResponse)
async def recommend_templates_for_task(
    request: RecommendRequest
):
    """
    Recommends the best templates from the library for a given task.
    """
    recommendations = await llm_service.recommend_templates(request)
    return RecommendResponse(recommendations=recommendations)

@router.delete("/{template_id}", status_code=204)
async def delete_single_template(template_id: str):
    """Deletes a single prompt template by its ID."""
    await firestore_service.delete_template_by_id(template_id)
    return Response(status_code=204)
# app/routers/sandbox.py
from fastapi import APIRouter, Depends, status # Add status
from typing import Dict, Any
from app.services import llm_service, security_service
from app.schemas.prompt import (
    PromptComposeRequest,
    PromptComposeResponse,
    TemplateGenerateRequest,
    RecommendRequest,
    RecommendResponse,
    SandboxRequest,
    SandboxResponse,
    PromptTemplate # Import the correct response model
)

router = APIRouter(
    tags=["Sandbox"],
)

@router.post("/compose", response_model=PromptComposeResponse)
async def compose_prompt_from_template(request: PromptComposeRequest):
    """(PUBLIC) Composes a final prompt string from a template and its variables."""
    return await llm_service.compose_prompt(request)

# FIX: Correct the response_model, status_code, and the service function call.
@router.post("/generate-template", response_model=PromptTemplate, status_code=status.HTTP_201_CREATED)
async def generate_template_from_prompt(
    request: TemplateGenerateRequest,
    # Add the user dependency, as creating a template requires an owner.
    current_user: Dict[str, Any] = Depends(security_service.get_current_user)
):
    """(SECURE) Generates and stores a new template using an LLM."""
    # Call the correct function name from the llm_service.
    created_template = await llm_service.generate_and_store_template(request, current_user)
    return created_template

@router.post("/recommend-templates", response_model=RecommendResponse)
async def recommend_templates_for_prompt(request: RecommendRequest):
    """(PUBLIC) Recommends the top 3 templates for a given prompt."""
    recommendations = await llm_service.recommend_templates(request)
    return RecommendResponse(recommendations=recommendations)

@router.post("/run", response_model=SandboxResponse)
async def run_sandbox_comparison(request: SandboxRequest):
    """(PUBLIC) Runs a side-by-side comparison of multiple prompts."""
    results = await llm_service.run_sandbox_test(request)
    return SandboxResponse(results=results)
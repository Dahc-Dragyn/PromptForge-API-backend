# app/routers/sandbox.py
from fastapi import APIRouter, Depends
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
)

router = APIRouter(
    tags=["Sandbox"],
)

@router.post("/compose", response_model=PromptComposeResponse)
async def compose_prompt_from_template(request: PromptComposeRequest):
    """(PUBLIC) Composes a final prompt string from a template and its variables."""
    # FIX: Pass the entire 'request' object to the service function as expected.
    return await llm_service.compose_prompt(request)

@router.post("/generate-template", response_model=PromptComposeResponse)
async def generate_template_from_prompt(request: TemplateGenerateRequest):
    """(PUBLIC) Generates a reusable template from a given raw prompt."""
    generated_template = await llm_service.generate_template_from_prompt(request)
    return PromptComposeResponse(composed_prompt=generated_template) # Corrected response model usage

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
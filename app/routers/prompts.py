# app/routers/prompts.py
from fastapi import APIRouter, Depends, HTTPException, Response
from google.cloud.firestore_v1.async_client import AsyncClient
from typing import List, Dict, Any
from datetime import datetime
import uuid

from app.core.db import get_firestore_client
from app.schemas.prompt import (
    Prompt,
    PromptCreate,
    PromptUpdate,
    PromptVersion,
    PromptVersionCreate,
    PromptExecuteRequest,
    PromptExecution,  # <-- FIX: Import the correct, detailed schema
    APEOptimizeRequest,
    APEOptimizeResponse,
    BenchmarkRequest,
    BenchmarkResponse,
    DiagnoseRequest,
    DiagnoseResponse,
    BreakdownRequest,
    BreakdownResponse,
    PromptTemplate,
    PromptTemplateCreate,
    PromptComposeRequest,
    PromptComposeResponse
)
from app.services import firestore_service, llm_service

router = APIRouter(
    prefix="/prompts",
    tags=["Prompts"],
)

# === CRUD and Versioning Endpoints ===

@router.post("/", response_model=Prompt, status_code=201)
async def create_new_prompt(prompt: PromptCreate):
    """Create a new prompt record and its first version."""
    created_prompt = await firestore_service.create_prompt(prompt)
    return created_prompt

@router.get("/", response_model=List[Prompt])
async def get_all_prompts():
    """Retrieve all prompt records from the library."""
    prompts = await firestore_service.list_prompts()
    return prompts

@router.get("/{prompt_id}", response_model=Prompt)
async def get_single_prompt(prompt_id: str):
    """Retrieve a single prompt by its ID."""
    prompt = await firestore_service.get_prompt_by_id(prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt

@router.patch("/{prompt_id}", response_model=Prompt)
async def update_single_prompt(prompt_id: str, prompt_update: PromptUpdate):
    """Updates a single prompt's metadata (name or description)."""
    updated_prompt = await firestore_service.update_prompt_by_id(prompt_id, prompt_update)
    if not updated_prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return updated_prompt

@router.delete("/{prompt_id}", status_code=204)
async def delete_single_prompt(prompt_id: str):
    """Deletes a single prompt by its ID."""
    await firestore_service.delete_prompt_by_id(prompt_id)
    return Response(status_code=204)

@router.get("/{prompt_id}/versions", response_model=List[PromptVersion], tags=["Versioning"])
async def get_prompt_versions(prompt_id: str):
    """Lists all versions of a specific prompt."""
    parent_prompt = await firestore_service.get_prompt_by_id(prompt_id)
    if not parent_prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    versions = await firestore_service.list_prompt_versions(prompt_id)
    return versions

@router.post("/{prompt_id}/versions", response_model=PromptVersion, status_code=201, tags=["Versioning"])
async def create_new_version_for_prompt(prompt_id: str, version_data: PromptVersionCreate, db: AsyncClient = Depends(get_firestore_client)):
    transaction = db.transaction()
    try:
        new_version = await firestore_service.create_new_prompt_version(transaction, prompt_id, version_data)
        return new_version
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


# === LLM Endpoints ===

# --- THIS IS THE FUNCTION TO FIX ---
@router.post("/execute", response_model=PromptExecution, tags=["Execution"])
async def execute_prompt_with_llm(request: PromptExecuteRequest):
    """
    Executes a prompt for one-off runs and returns a full PromptExecution object.
    """
    try:
        # Step 1: Call the updated service function with the full request object
        return await llm_service.execute_managed_prompt(
            request=request, 
            user_id="temp-user-id" # Placeholder user ID for a one-off run
        )

    except HTTPException as e:
        # Re-raise HTTPExceptions from the service layer
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred during prompt execution: {str(e)}")


@router.post("/optimize", response_model=APEOptimizeResponse, tags=["APE"])
async def optimize_prompt_with_ape(request: APEOptimizeRequest):
    """Generates an optimized prompt based on a task description and examples."""
    result_dict = await llm_service.generate_optimized_prompt(request)
    return APEOptimizeResponse(**result_dict)


@router.post("/benchmark", response_model=BenchmarkResponse, tags=["Benchmark"])
async def benchmark_prompt_performance(request: BenchmarkRequest):
    results = await llm_service.benchmark_prompt(request)
    return BenchmarkResponse(results=results)


@router.post("/diagnose", response_model=DiagnoseResponse, tags=["Analysis"])
async def diagnose_prompt_quality(request: DiagnoseRequest):
    diagnosis_result = await llm_service.diagnose_prompt(request)
    return DiagnoseResponse(**diagnosis_result)


@router.post("/breakdown", response_model=BreakdownResponse, tags=["Analysis"])
async def breakdown_prompt_structure(request: BreakdownRequest):
    breakdown_result = await llm_service.breakdown_prompt(request)
    return BreakdownResponse(**breakdown_result)
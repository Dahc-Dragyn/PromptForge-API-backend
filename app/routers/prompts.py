# app/routers/prompts.py
from fastapi import APIRouter, Depends, HTTPException, Response
from typing import List, Dict

# Your own project's imports
from app.services import firestore_service, llm_service, security_service
from app.schemas.prompt import (
    Prompt, PromptCreate, PromptUpdate, PromptVersion, PromptVersionCreate,
    PromptExecuteRequest, PromptExecution, APEOptimizeRequest, APEOptimizeResponse,
    BenchmarkRequest, BenchmarkResponse, DiagnoseRequest, DiagnoseResponse,
    BreakdownRequest, BreakdownResponse
)

router = APIRouter(
    tags=["Prompts"],
)

# --- Reusable Security Dependencies ---
get_current_user_dependency = Depends(security_service.get_current_user)
prompt_owner_or_admin_dependency = Depends(security_service.PromptOwnerOrAdmin())

# === CRUD and Versioning Endpoints ===

@router.post("/", response_model=Prompt, status_code=201)
async def create_new_prompt(
    prompt: PromptCreate,
    current_user: Dict = get_current_user_dependency
):
    """(SECURE) Create a new prompt for the authenticated user."""
    return await firestore_service.create_prompt(prompt, user=current_user)

# V-- THIS IS THE LINE THAT FIXES THE CRASH --V
@router.get("/", response_model=List[Prompt])
async def get_all_prompts_for_user(
    current_user: Dict = get_current_user_dependency
):
# ^-- THE FIX IS response_model=List[Prompt] --^
    """(SECURE) Retrieve all prompts owned by the authenticated user."""
    user_id = current_user["uid"]
    return await firestore_service.list_prompts_for_user(user_id)

@router.get("/{prompt_id}", response_model=Prompt)
async def get_single_prompt(
    prompt_id: str,
    _ = prompt_owner_or_admin_dependency
):
    """(SECURE) Retrieve a single prompt by ID. Requires ownership."""
    prompt = await firestore_service.get_prompt_by_id(prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt

@router.patch("/{prompt_id}", response_model=Prompt)
async def update_single_prompt(
    prompt_id: str,
    prompt_update: PromptUpdate,
    _ = prompt_owner_or_admin_dependency
):
    """(SECURE) Update a prompt's metadata. Requires ownership."""
    updated_prompt = await firestore_service.update_prompt_by_id(prompt_id, prompt_update)
    if not updated_prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return updated_prompt

@router.delete("/{prompt_id}", status_code=204)
async def delete_single_prompt(
    prompt_id: str,
    _ = prompt_owner_or_admin_dependency
):
    """(SECURE) Delete a prompt by ID. Requires ownership."""
    await firestore_service.delete_prompt_by_id(prompt_id)
    return Response(status_code=204)

@router.get("/{prompt_id}/versions", response_model=List[PromptVersion], tags=["Versioning"])
async def get_prompt_versions(
    prompt_id: str,
    _ = prompt_owner_or_admin_dependency
):
    """(SECURE) List all versions of a specific prompt. Requires ownership."""
    return await firestore_service.list_prompt_versions(prompt_id)

@router.post("/{prompt_id}/versions", response_model=PromptVersion, status_code=201, tags=["Versioning"])
async def create_new_version_for_prompt(
    prompt_id: str,
    version_data: PromptVersionCreate,
    current_user: Dict = prompt_owner_or_admin_dependency
):
    """(SECURE) Create a new version for a prompt. Requires ownership."""
    try:
        return await firestore_service.create_new_prompt_version(
            prompt_id, version_data, user=current_user
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

# === LLM Endpoints (Public) ===

@router.post("/execute", response_model=PromptExecution, tags=["Execution"])
async def execute_prompt_with_llm(request: PromptExecuteRequest):
    return await llm_service.execute_platform_prompt(request=request)

@router.post("/optimize", response_model=APEOptimizeResponse, tags=["APE"])
async def optimize_prompt_with_ape(request: APEOptimizeRequest):
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
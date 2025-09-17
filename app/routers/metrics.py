# app/routers/metrics.py
from fastapi import APIRouter, Depends 
from typing import Dict 
from app.schemas.prompt import (
    CostCalculationRequest, 
    CostCalculationResponse,
    PromptsSummaryResponse
)
# --- FIX 1: Import the new security dependencies ---
from app.services import cost_service, firestore_service, security_service

router = APIRouter(
    prefix="/metrics",
    tags=["Metrics"],
)

@router.get("/summary", response_model=PromptsSummaryResponse)
async def get_prompts_summary():
    """
    Retrieves a list of all prompts with aggregated analytics.
    """
    summary_results = await firestore_service.get_prompts_summary()
    return PromptsSummaryResponse(results=summary_results)

@router.post("/calculate-cost", response_model=CostCalculationResponse)
async def get_cost_estimate(request: CostCalculationRequest):
    """
    Calculates the estimated cost of an LLM call based on the model and token count.
    """
    return await cost_service.calculate_cost(request)


# --- FIX 2: Add a new admin-only endpoint ---
@router.get("/admin/user-report", tags=["Admin"])
async def get_admin_user_report(
    admin_user: Dict = Depends(security_service.require_admin_role)
):
    """
    (ADMIN ONLY) A placeholder endpoint to demonstrate RBAC.
    In a real app, this would return a summary of all user activity.
    """
    # The user's identity is available in the admin_user dictionary
    admin_uid = admin_user.get("uid")
    
    return {
        "message": "Welcome, admin. This is a protected report.",
        "admin_user_uid": admin_uid,
        "report_data": {
            "total_users": 1, # Placeholder
            "total_prompts_executed": 100 # Placeholder
        }
    }
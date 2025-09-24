# app/routers/metrics.py
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List
from app.schemas.prompt import (
    CostCalculationRequest,
    CostCalculationResponse,
    RecentActivity,
    PromptSummary,
    RatingCreate
)
from app.services import cost_service, firestore_service, security_service

router = APIRouter(
    prefix="/metrics",
    tags=["Metrics"],
)

# The correct endpoint path the frontend expects
@router.get("/prompts/top", response_model=List[PromptSummary])
async def get_top_prompts(user: Dict = Depends(security_service.get_current_user)):
    """
    Retrieves a list of all prompts for the current user with aggregated analytics.
    """
    summary_results = await firestore_service.get_prompt_summary_with_ratings(user['uid'])
    return summary_results

@router.get("/activity/recent", response_model=List[RecentActivity])
async def get_recent_activity(user: Dict = Depends(security_service.get_current_user)):
    """
    Retrieves the most recently updated or created prompt versions for the current user.
    """
    activity_results = await firestore_service.get_recent_activity(user['uid'])
    return activity_results

@router.post("/ratings", status_code=201)
async def submit_rating(rating_data: RatingCreate, user: Dict = Depends(security_service.get_current_user)):
    """
    Submits a new rating for a specific prompt version.
    """
    try:
        rating_id = await firestore_service.create_rating_for_version(
            user_id=user['uid'],
            prompt_id=rating_data.prompt_id,
            version_number=rating_data.version_number,
            rating_value=rating_data.rating
        )
        return {"status": "success", "rating_id": rating_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit rating: {str(e)}")


@router.post("/calculate-cost", response_model=CostCalculationResponse)
async def get_cost_estimate(request: CostCalculationRequest):
    """
    Calculates the estimated cost of an LLM call based on the model and token count.
    """
    return await cost_service.calculate_cost(request)

@router.get("/admin/user-report", tags=["Admin"])
async def get_admin_user_report(
    admin_user: Dict = Depends(security_service.require_admin_role)
):
    """
    (ADMIN ONLY) A placeholder endpoint to demonstrate RBAC.
    """
    admin_uid = admin_user.get("uid")
    return {
        "message": "Welcome, admin. This is a protected report.",
        "admin_user_uid": admin_uid,
        "report_data": {
            "total_users": 1,
            "total_prompts_executed": 100
        }
    }
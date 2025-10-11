# app/routers/metrics.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from app.services import firestore_service, security_service
from app.schemas.prompt import PromptSummary, RecentActivity, RatingCreate

router = APIRouter(
    prefix="/metrics",
    tags=["Metrics"],
)

@router.get("/prompts/all", response_model=List[PromptSummary])
async def get_all_prompts_metrics():
    """(PUBLIC) Retrieves summary metrics for all non-deleted prompts."""
    prompts_data = await firestore_service.get_all_prompt_metrics()
    return [PromptSummary(**prompt) for prompt in prompts_data]

@router.get("/prompts/starred", response_model=List[PromptSummary])
async def get_starred_prompts_for_user(
    current_user: Dict = Depends(security_service.get_current_user)
):
    """(SECURE) Retrieves highly-rated (starred) prompts for the current user."""
    user_id = current_user["uid"]
    prompts_data = await firestore_service.list_starred_prompts_for_user(user_id)
    return [PromptSummary(**prompt) for prompt in prompts_data]

# V-- THIS IS THE CORRECTED, SECURE ENDPOINT --V
@router.get("/activity/recent", response_model=List[RecentActivity])
async def get_recent_user_activity(
    limit: int = 10,
    current_user: Dict = Depends(security_service.get_current_user)
):
    """(SECURE) Retrieves recent activity for the currently authenticated user."""
    user_id = current_user["uid"]
    return await firestore_service.get_recent_activity_for_user(user_id, limit)
# ^-- END OF CORRECTION --^

@router.post("/rate", status_code=201)
async def rate_prompt_version(
    rating_data: RatingCreate,
    current_user: Dict = Depends(security_service.get_current_user)
):
    """(SECURE) Creates or updates a rating for a specific prompt version."""
    user_id = current_user["uid"]
    try:
        await firestore_service.create_or_update_rating(
            prompt_id=rating_data.prompt_id,
            version_number=rating_data.version_number,
            rating=rating_data.rating,
            user_id=user_id
        )
        return {"message": "Rating submitted successfully."}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
# app/routers/metrics.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any

from app.schemas.prompt import RatingCreate
from app.services import firestore_service, security_service
from app.core.db import db

router = APIRouter(
    tags=["Metrics"],
)

@router.get("/prompts/all", response_model=List[Dict[str, Any]])
async def get_all_prompt_metrics():
    """(PUBLIC) Retrieves aggregated metrics for all prompts."""
    try:
        metrics = await firestore_service.get_all_prompt_metrics()
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/activity/recent", response_model=List[Dict[str, Any]])
async def get_recent_activity():
    """(PUBLIC) Fetches the 10 most recently updated prompts or templates."""
    try:
        activity = await firestore_service.get_recent_activity()
        return activity
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rate", status_code=status.HTTP_201_CREATED)
async def rate_prompt_version(
    rating_data: RatingCreate,
    current_user: Dict = Depends(security_service.get_current_user)
):
    """
    (SECURE) Creates or updates a rating for a specific prompt version.
    """
    try:
        # --- FINAL FIX: Call the function directly, passing db.transaction() as the first argument ---
        await firestore_service.create_or_update_rating(
            db.transaction(), # This is where the transaction object is passed
            prompt_id=rating_data.prompt_id,
            version_number=rating_data.version_number,
            rating=rating_data.rating,
            user_id=current_user["uid"]
        )
        return {"message": "Rating submitted successfully"}
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )
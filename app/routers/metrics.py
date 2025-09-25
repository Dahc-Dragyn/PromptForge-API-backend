# app/routers/metrics.py
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from app.services import firestore_service

# FIX: The 'prefix' argument is removed.
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
        # It's better to log the exception here
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/activity/recent", response_model=List[Dict[str, Any]])
async def get_recent_activity():
    """(PUBLIC) Fetches the 10 most recently updated prompts or templates."""
    try:
        activity = await firestore_service.get_recent_activity()
        return activity
    except Exception as e:
        # It's better to log the exception here
        raise HTTPException(status_code=500, detail=str(e))
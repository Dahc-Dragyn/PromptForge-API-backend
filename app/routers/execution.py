# app/routers/execution.py
from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict

from app.schemas.prompt import (
    ManagedExecutionRequest,
    PromptExecuteResponse,
    UserAPIKey
)
from app.services import llm_service, firestore_service, security_service

# FIX: The 'prefix' argument is removed.
router = APIRouter(
    tags=["User Management & Execution"],
)

@router.post("/execute", response_model=PromptExecuteResponse)
async def execute_managed_prompt(
    request: ManagedExecutionRequest,
    current_user: Dict = Depends(security_service.get_current_user)
):
    """
    (SECURE) Executes a prompt using the authenticated user's stored API key.
    """
    if current_user["uid"] != request.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to execute prompts for this user."
        )

    try:
        result = await llm_service.execute_managed_prompt(
            user_id=current_user["uid"],
            model_name=request.model_name,
            prompt_text=request.prompt_text
        )
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@router.post("/{user_id}/keys", status_code=status.HTTP_204_NO_CONTENT)
async def save_user_api_key(
    user_id: str,
    key_data: UserAPIKey,
    current_user: Dict = Depends(security_service.get_current_user)
):
    """
    (SECURE) Saves and encrypts a user's API key for a specific provider.
    """
    if current_user["uid"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to modify this resource."
        )

    try:
        await firestore_service.save_user_api_key(
            user_id=user_id,
            provider=key_data.provider,
            api_key=key_data.api_key
        )
        return
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save API key: {str(e)}")
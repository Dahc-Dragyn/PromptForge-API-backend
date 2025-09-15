from fastapi import APIRouter, HTTPException, status
from app.schemas.prompt import (
    ManagedExecutionRequest,
    PromptExecuteResponse,
    UserAPIKey
)
from app.services import llm_service, firestore_service

# --- FIX: Initialize the router with a prefix and tags for user management ---
router = APIRouter(
    prefix="/users",
    tags=["User Management"],
)

@router.post("/execute", response_model=PromptExecuteResponse, tags=["Execution"])
async def execute_managed_prompt(request: ManagedExecutionRequest):
    """
    Executes a prompt against a specified model using a user's stored API key.
    """
    try:
        result = await llm_service.execute_managed_prompt(
            user_id=request.user_id,
            model_name=request.model_name,
            prompt_text=request.prompt_text
        )
        return result
    except HTTPException as e:
        # Re-raise HTTPExceptions to let FastAPI handle the response
        raise e
    except Exception as e:
        # Catch any other unexpected errors
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


# This endpoint will now correctly be at POST /api/promptforge/users/{user_id}/keys
@router.post("/{user_id}/keys", status_code=status.HTTP_204_NO_CONTENT)
async def save_user_api_key(user_id: str, key_data: UserAPIKey):
    """
    Saves and encrypts a user's API key for a specific provider.
    """
    try:
        await firestore_service.save_user_api_key(
            user_id=user_id,
            provider=key_data.provider,
            api_key=key_data.api_key
        )
        return
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save API key: {str(e)}")
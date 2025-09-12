from fastapi import APIRouter
from app.schemas.prompt import SandboxRequest, SandboxResponse
from app.services import llm_service

router = APIRouter(
    prefix="/sandbox",
    tags=["Sandbox"],
)

@router.post("/", response_model=SandboxResponse)
async def run_prompt_sandbox(
    request: SandboxRequest
):
    """
    Runs an A/B test on multiple prompt variations against a single model.
    """
    results = await llm_service.run_sandbox_test(request)
    return SandboxResponse(results=results)
from fastapi import APIRouter
from app.schemas.prompt import (
    CostCalculationRequest, 
    CostCalculationResponse,
    PromptsSummaryResponse
)
from app.services import cost_service, firestore_service

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
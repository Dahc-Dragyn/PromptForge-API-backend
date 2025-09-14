from fastapi import APIRouter
from app.schemas.prompt import CostCalculationRequest, CostCalculationResponse
from app.services import cost_service

router = APIRouter(
    prefix="/metrics",
    tags=["Metrics"],
)

@router.post("/calculate-cost", response_model=CostCalculationResponse)
async def get_cost_estimate(request: CostCalculationRequest):
    """
    Calculates the estimated cost of an LLM call based on the model and token count.
    """
    return await cost_service.calculate_cost(request)
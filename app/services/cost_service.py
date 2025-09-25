# app/services/cost_service.py
import logging
from fastapi import HTTPException
from app.schemas.prompt import CostCalculationRequest, CostCalculationResponse
from app.core.db import db

# --- Pricing Data (Simplified) ---
PRICING_DATA = {
    "gemini-1.5-flash": {"input_per_million": 0.35, "output_per_million": 0.70},
    "gemini-1.5-pro-latest": {"input_per_million": 3.50, "output_per_million": 10.50},
    "gpt-4o-mini": {"input_per_million": 0.15, "output_per_million": 0.60},
    "default": {"input_per_million": 1.00, "output_per_million": 3.00}
}

async def calculate_cost(request: CostCalculationRequest) -> CostCalculationResponse:
    """Calculates the estimated cost of an LLM call based on token counts."""
    pricing = PRICING_DATA.get(request.model_name, PRICING_DATA["default"])
    input_cost = (request.input_token_count / 1_000_000) * pricing["input_per_million"]
    output_cost = (request.output_token_count / 1_000_000) * pricing["output_per_million"]
    total_cost = input_cost + output_cost
    
    return CostCalculationResponse(
        model_name=request.model_name,
        input_token_count=request.input_token_count,
        output_token_count=request.output_token_count,
        estimated_cost_usd=total_cost
    )

# FIX: Add the function that llm_service is trying to call.
async def calculate_cost_from_tokens(model_name: str, input_tokens: int, output_tokens: int) -> float:
    """A direct utility function to calculate cost from raw token counts."""
    request = CostCalculationRequest(
        model_name=model_name,
        input_token_count=input_tokens,
        output_token_count=output_tokens
    )
    response = await calculate_cost(request)
    return response.estimated_cost_usd
from app.core.db import db
from app.schemas.prompt import CostCalculationRequest, CostCalculationResponse

# --- Constants ---
PRICING_COLLECTION = "llm_pricing"

async def calculate_cost(request: CostCalculationRequest) -> CostCalculationResponse:
    """
    Calculates the estimated cost by fetching granular input/output pricing data from Firestore.
    """
    pricing_doc_ref = db.collection(PRICING_COLLECTION).document(request.model_name)
    pricing_doc = await pricing_doc_ref.get()

    estimated_cost = 0.0

    if pricing_doc.exists:
        pricing_data = pricing_doc.to_dict()
        
        # Get separate prices for input and output, defaulting to 0.0 if a price is missing
        price_per_million_input = pricing_data.get("price_per_million_input_tokens_usd", 0.0)
        price_per_million_output = pricing_data.get("price_per_million_output_tokens_usd", 0.0)

        # --- New Calculation Logic ---
        input_cost = (request.input_token_count / 1_000_000) * price_per_million_input
        output_cost = (request.output_token_count / 1_000_000) * price_per_million_output
        estimated_cost = input_cost + output_cost

    return CostCalculationResponse(
        model_name=request.model_name,
        input_token_count=request.input_token_count,
        output_token_count=request.output_token_count,
        estimated_cost_usd=estimated_cost
    )
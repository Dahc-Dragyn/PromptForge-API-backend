# app/schemas/prompt.py
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Any, Dict

# --- Prompt Version Schemas ---
class PromptVersionBase(BaseModel):
    prompt_text: str

class PromptVersionCreate(PromptVersionBase):
    commit_message: Optional[str] = None

class PromptVersion(PromptVersionBase):
    id: str
    prompt_id: str
    version_number: int
    created_at: datetime
    commit_message: Optional[str] = None
    class Config:
        from_attributes = True

# --- Main Prompt Schemas ---
# This is the original, correct base model
class PromptBase(BaseModel):
    name: str
    task_description: str

# This is the original, correct creation model that the test script uses
class PromptCreate(PromptBase):
    initial_prompt_text: str

class Prompt(PromptBase):
    id: str
    created_at: datetime
    latest_version: int
    class Config:
        from_attributes = True

class PromptUpdate(BaseModel):
    name: Optional[str] = None
    task_description: Optional[str] = None

# --- Execution Schemas ---
# This is the new, rich data model that the frontend needs for executions
class PromptExecution(BaseModel):
    id: str
    prompt_version_id: str
    executed_at: datetime
    raw_response: Dict[str, Any]
    final_text: str
    input_token_count: int
    output_token_count: int
    latency_ms: int
    cost: float
    rating: Optional[int] = Field(None, ge=1, le=5)
    class Config:
        from_attributes = True

# The request from the frontend needs the 'model' and 'variables' fields
class PromptExecuteRequest(BaseModel):
    prompt_text: str = Field(..., example="Explain quantum computing in simple terms.")
    model: str = Field(..., example="gemini-1.5-pro-latest")
    variables: Dict[str, Any] = Field({}, description="Key-value pairs for variables.")

# The old response type is now an alias for our new, better one.
PromptExecuteResponse = PromptExecution

# --- Managed Execution Schemas ---
class ManagedExecutionRequest(BaseModel):
    user_id: str = Field(..., example="some_firebase_user_id")
    model_name: str = Field(..., example="gpt-4o-mini")
    prompt_text: str = Field(..., example="Explain the theory of relativity.")

class UserAPIKey(BaseModel):
    provider: str = Field(..., example="openai")
    api_key: str = Field(..., example="sk-...")


# --- APE Schemas ---
class APEExample(BaseModel):
    input: str = Field(..., example="Customer review: 'The product is amazing!'")
    output: str = Field(..., example="Sentiment: Positive")

class APEOptimizeRequest(BaseModel):
    task_description: str = Field(..., example="Classify the sentiment of a customer review.")
    examples: List[APEExample]

class APEOptimizeResponse(BaseModel):
    optimized_prompt: str
    reasoning_summary: str
    performance_score: Optional[float] = None

# --- Analysis Schemas ---
class DiagnoseRequest(BaseModel):
    prompt_text: str = Field(..., example="Make a story.")

class ScoreCriteria(BaseModel):
    clarity: bool
    specificity: bool
    context: bool
    constraints: bool

class DiagnoseResponse(BaseModel):
    overall_score: float = Field(..., ge=0, le=10)
    diagnosis: str
    key_issues: List[str]
    suggested_prompt: str
    criteria: ScoreCriteria

class BreakdownRequest(BaseModel):
    prompt_text: str = Field(..., example="You are a helpful assistant. Summarize...")

class BreakdownComponent(BaseModel):
    type: str
    content: Any
    explanation: str

class BreakdownResponse(BaseModel):
    components: List[BreakdownComponent]

# --- Template Library Schemas ---
class TagCategory(str, Enum):
    TASK = "Task"
    STYLE_TONE = "Style/Tone"
    PERSONA = "Persona"
    OUTPUT_FORMAT = "Output Format"
    DOMAIN = "Domain"
    LANGUAGE = "Language"

class Tag(BaseModel):
    name: str = Field(..., example="summarize")
    category: TagCategory

class PromptTemplateBase(BaseModel):
    name: str = Field(..., example="Professional Email Summarizer")
    description: str
    content: str
    tags: List[str] = Field(..., example=["summarize", "formal", "email_format"])

class PromptTemplateCreate(PromptTemplateBase):
    pass

class PromptTemplate(PromptTemplateBase):
    id: str
    created_at: datetime
    version: int = 1
    class Config:
        from_attributes = True

class TemplateGenerateRequest(BaseModel):
    style_description: str = Field(..., example="A formal persona for summarizing legal documents.")
    tags: Optional[List[str]] = Field(None)

class PromptComposeRequest(BaseModel):
    task: Optional[str] = Field(None, example="summarize")
    style: Optional[str] = Field(None, example="academic")
    persona: Optional[str] = Field(None, example="expert_researcher")
    output_format: Optional[str] = Field(None, example="bullet_points")
    domain: Optional[str] = Field(None, example="science")
    language: Optional[str] = Field(None, example="en")

class PromptComposeResponse(BaseModel):
    composed_prompt: str
    source_templates: Optional[List[str]] = None

# --- Sandbox & Benchmark Schemas ---
class BenchmarkRequest(BaseModel):
    prompt_text: str = Field(..., example="Write a short story about a robot who discovers music.")
    models: List[str] = Field(..., example=["gemini-2.5-flash-lite", "gpt-4o-mini"])

class BenchmarkResult(BaseModel):
    model_name: str
    generated_text: str
    latency_ms: float
    input_token_count: Optional[int] = None
    output_token_count: Optional[int] = None

class BenchmarkResponse(BaseModel):
    results: List[BenchmarkResult]

class SandboxPromptInput(BaseModel):
    id: str = Field(..., description="A unique identifier for this prompt, e.g., 'prompt_v1'.")
    text: str

class SandboxRequest(BaseModel):
    prompts: List[SandboxPromptInput]
    input_text: str
    model: str = Field(..., example="gemini-2.5-flash-lite")

class SandboxResult(BaseModel):
    prompt_id: str
    generated_text: str
    latency_ms: float
    input_token_count: Optional[int] = None
    output_token_count: Optional[int] = None

class SandboxResponse(BaseModel):
    results: List[SandboxResult]

class RecommendRequest(BaseModel):
    """The request body for the /templates/recommend endpoint."""
    task_description: str = Field(..., example="I need to write a professional email to a client.")

class RecommendedTemplate(BaseModel):
    """A single recommended template with a reason."""
    template: PromptTemplate
    reason: str

class RecommendResponse(BaseModel):
    """The response from the /templates/recommend endpoint."""
    recommendations: List[RecommendedTemplate]

# --- Metrics & Analytics Schemas ---
class CostCalculationRequest(BaseModel):
    model_name: str = Field(..., example="gemini-2.5-flash-lite")
    input_token_count: int = Field(..., example=1000)
    output_token_count: int = Field(..., example=500)

class CostCalculationResponse(BaseModel):
    model_name: str
    input_token_count: int
    output_token_count: int
    estimated_cost_usd: float

class PromptSummary(Prompt):
    version_count: int
    average_rating: float
    rating_count: int

class PromptsSummaryResponse(BaseModel):
    results: List[PromptSummary]
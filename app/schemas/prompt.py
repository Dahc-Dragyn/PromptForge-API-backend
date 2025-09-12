from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Any

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
class PromptBase(BaseModel):
    name: str
    task_description: str

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
class PromptExecuteRequest(BaseModel):
    prompt_text: str = Field(..., example="Explain quantum computing in simple terms.")

class PromptExecuteResponse(BaseModel):
    generated_text: str

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
    clarity: float = Field(..., ge=0, le=10)
    specificity: float = Field(..., ge=0, le=10)
    context: float = Field(..., ge=0, le=10)
    constraints: float = Field(..., ge=0, le=10)

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
    models: List[str] = Field(..., example=["gemini-2.5-flash-lite", "gpt-4.1-nano"])

class BenchmarkResult(BaseModel):
    model_name: str
    generated_text: str
    latency_ms: float
    token_count: Optional[int] = None

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

class SandboxResponse(BaseModel):
    results: List[SandboxResult]

# In app/schemas/prompt.py

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
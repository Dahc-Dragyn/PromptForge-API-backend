# app/services/llm_service.py
import os
import asyncio
import time
import json
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

import google.generativeai as genai
from openai import AsyncOpenAI
from fastapi import HTTPException
from uuid import uuid4

from app.services import cost_service, firestore_service
from app.schemas.prompt import (
    BenchmarkRequest, BenchmarkResult, APEOptimizeRequest,
    DiagnoseRequest, BreakdownRequest, TemplateGenerateRequest,
    PromptTemplateCreate, RecommendRequest, SandboxRequest,
    SandboxResult, SandboxPromptInput, PromptExecuteResponse, PromptExecuteRequest
)
from app.core.db import db

# --- Constants & Configuration (Unchanged) ---
DEFAULT_GEMINI_MODEL = 'gemini-2.5-flash-lite'
API_CACHE_COLLECTION = "api_cache"
CACHE_DURATION_MINUTES = 60

# --- Configuration (Unchanged) ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Global Platform Clients (Unchanged) ---
try:
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    platform_gemini_client = genai.GenerativeModel(DEFAULT_GEMINI_MODEL)
except Exception as e:
    logging.error(f"Could not configure Google AI: {e}")
    platform_gemini_client = None
try:
    platform_openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception as e:
    logging.error(f"Could not configure OpenAI: {e}")
    platform_openai_client = None

# --- Core LLM Call Functions (Unchanged) ---
async def _call_gemini_with_client(client: genai.GenerativeModel, prompt_text: str) -> tuple[str, int, int]:
    # ... (code is unchanged)
    input_token_count_response = await client.count_tokens_async(prompt_text)
    input_tokens = input_token_count_response.total_tokens
    response = await client.generate_content_async(prompt_text)
    generated_text = response.text
    output_token_count_response = await client.count_tokens_async(generated_text)
    output_tokens = output_token_count_response.total_tokens
    return generated_text, input_tokens, output_tokens

async def _call_openai_with_client(client: AsyncOpenAI, model_name: str, prompt_text: str) -> tuple[str, int, int]:
    # ... (code is unchanged)
    response = await client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt_text}]
    )
    generated_text = response.choices[0].message.content
    input_tokens = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens
    return generated_text, input_tokens, output_tokens

# --- Main Service Functions ---

# --- THIS IS THE FUNCTION TO UPDATE ---
async def execute_managed_prompt(user_id: str, model_name: str, prompt_text: str) -> PromptExecuteResponse:
    """
    Executes a prompt using a specific user's securely stored API key.
    The user_id provided here is trusted because it comes from the authenticated token.
    """
    provider = "google" if model_name.startswith("gemini") else "openai"
    
    decrypted_key = await firestore_service.get_decrypted_user_api_key(user_id, provider)
    if not decrypted_key:
        raise HTTPException(status_code=403, detail=f"API key for provider '{provider}' not found or invalid for this user.")

    generated_text, input_tokens, output_tokens = "An error occurred.", 0, 0
    start_time = time.perf_counter()

    try:
        if provider == "google":
            genai.configure(api_key=decrypted_key)
            user_client = genai.GenerativeModel(model_name)
            generated_text, input_tokens, output_tokens = await _call_gemini_with_client(user_client, prompt_text)
        elif provider == "openai":
            user_client = AsyncOpenAI(api_key=decrypted_key)
            generated_text, input_tokens, output_tokens = await _call_openai_with_client(user_client, model_name, prompt_text)
        
        end_time = time.perf_counter()
        latency_ms = (end_time - start_time) * 1000

        cost_request = cost_service.CostCalculationRequest(
            model_name=model_name,
            input_token_count=input_tokens,
            output_token_count=output_tokens
        )
        cost_response = await cost_service.calculate_cost(cost_request)
        cost = cost_response.estimated_cost_usd

    except Exception as e:
        logging.error(f"Managed execution failed for user {user_id} with model {model_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to execute prompt with the provided key: {str(e)}")

    return PromptExecuteResponse(
        id=str(uuid4()),
        prompt_version_id="managed-run", # Differentiate from platform runs
        executed_at=datetime.now(timezone.utc),
        raw_response={"text": generated_text},
        final_text=generated_text,
        input_token_count=input_tokens,
        output_token_count=output_tokens,
        latency_ms=int(latency_ms),
        cost=cost,
        rating=None
    )


# --- Platform & Other Services (All Unchanged) ---
async def execute_platform_prompt(request: PromptExecuteRequest) -> PromptExecuteResponse:
    # ... (code is unchanged)
    provider = "google" if request.model.startswith("gemini") else "openai"
    generated_text, input_tokens, output_tokens = "An error occurred.", 0, 0
    start_time = time.perf_counter()
    try:
        if provider == "google":
            if not platform_gemini_client:
                raise ValueError("Google AI client is not configured.")
            client = genai.GenerativeModel(request.model)
            generated_text, input_tokens, output_tokens = await _call_gemini_with_client(client, request.prompt_text)
        elif provider == "openai":
            if not platform_openai_client:
                raise ValueError("OpenAI client is not configured.")
            generated_text, input_tokens, output_tokens = await _call_openai_with_client(platform_openai_client, request.model, request.prompt_text)
        end_time = time.perf_counter()
        latency_ms = (end_time - start_time) * 1000
        cost_request = cost_service.CostCalculationRequest(
            model_name=request.model,
            input_token_count=input_tokens,
            output_token_count=output_tokens
        )
        cost_response = await cost_service.calculate_cost(cost_request)
        cost = cost_response.estimated_cost_usd
    except Exception as e:
        logging.error(f"Platform execution failed for model {request.model}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to execute prompt with platform key: {str(e)}")
    return PromptExecuteResponse(
        id=str(uuid4()),
        prompt_version_id="platform-run",
        executed_at=datetime.now(timezone.utc),
        raw_response={"text": generated_text},
        final_text=generated_text,
        input_token_count=input_tokens,
        output_token_count=output_tokens,
        latency_ms=int(latency_ms),
        cost=cost,
        rating=None
    )

async def benchmark_prompt(request: BenchmarkRequest) -> list[BenchmarkResult]:
    # ... (code is unchanged)
    tasks = [execute_single_model_benchmark(model_name, request.prompt_text) for model_name in request.models]
    results = await asyncio.gather(*tasks)
    return results

# ... (The rest of the llm_service.py file remains the same) ...
async def execute_single_model_benchmark(model_name: str, prompt_text: str) -> BenchmarkResult:
    cache_key = hashlib.sha256(f"{model_name}:{prompt_text}".encode()).hexdigest()
    cache_ref = db.collection(API_CACHE_COLLECTION).document(cache_key)
    cached_doc = await cache_ref.get()

    if cached_doc.exists:
        cached_data = cached_doc.to_dict()
        if "created_at" in cached_data:
            cached_at = cached_data["created_at"]
            if datetime.now(timezone.utc) - cached_at < timedelta(minutes=CACHE_DURATION_MINUTES):
                logging.info(f"⚡️ Cache HIT for model {model_name}.")
                return BenchmarkResult(**cached_data.get("result", {}))

    logging.info(f"💸 Cache MISS for model {model_name}. Calling external API.")
    start_time = time.perf_counter()
    generated_text, input_token_count, output_token_count = "Error: Model not supported.", 0, 0
    try:
        if model_name.startswith("gemini"):
            client = genai.GenerativeModel(model_name)
            generated_text, input_token_count, output_token_count = await _call_gemini_with_client(client, prompt_text)
        elif model_name.startswith("gpt"):
            generated_text, input_token_count, output_token_count = await _call_openai_with_client(platform_openai_client, model_name, prompt_text)
    except Exception as e:
        logging.error(f"API call failed for {model_name}: {e}")
        generated_text = f"Error calling {model_name}: {str(e)}"

    end_time = time.perf_counter()
    latency_ms = (end_time - start_time) * 1000
    result = BenchmarkResult(model_name=model_name, generated_text=generated_text, latency_ms=latency_ms, input_token_count=input_token_count, output_token_count=output_token_count)
    await cache_ref.set({"created_at": datetime.now(timezone.utc), "result": result.model_dump()})
    return result

async def generate_optimized_prompt(request: APEOptimizeRequest) -> dict:
    model = genai.GenerativeModel(DEFAULT_GEMINI_MODEL)
    formatted_examples = "\n".join([f"INPUT: {ex.input}\nOUTPUT: {ex.output}\n" for ex in request.examples])
    meta_prompt = f"""
Your primary task is to act as an expert prompt engineer. Analyze the user's goal and examples, then create an optimized prompt.
You MUST respond with ONLY a single, valid JSON object.
The JSON object must contain these two keys: "optimized_prompt" and "reasoning_summary".
USER'S GOAL: {request.task_description}
EXAMPLES:\n{formatted_examples}
---
"""
    generation_config = genai.types.GenerationConfig(response_mime_type="application/json")
    try:
        response = await model.generate_content_async(meta_prompt, generation_config=generation_config)
        return json.loads(response.text)
    except Exception as e:
        logging.error(f"Error optimizing prompt: {e}")
        return {"optimized_prompt": "Error: Could not generate prompt.", "reasoning_summary": str(e)}

async def diagnose_prompt(request: DiagnoseRequest) -> dict:
    model = genai.GenerativeModel(DEFAULT_GEMINI_MODEL)
    meta_prompt = f"""
Your primary task is to analyze the prompt and return a JSON object with boolean flags for these criteria:
- "has_clear_goal": Is the language precise and the main task unambiguous?
- "provides_examples": Does the prompt include one or more specific examples of desired input/output?
- "specifies_constraints": Does the prompt specify limitations or requirements (e.g., length, format, style)?
- "provides_context": Does the prompt provide necessary background or situational details?
- "is_concise": Is the prompt succinct without unnecessary verbosity?

Also include a "diagnosis" key with a brief, one-sentence summary of the prompt's quality, and a "suggested_prompt" key with an improved version.
Respond with ONLY a JSON object like: {{"has_clear_goal": true, "provides_examples": false, "specifies_constraints": true, "provides_context": false, "is_concise": true, "diagnosis": "...", "suggested_prompt": "..."}}

Analyze this prompt:
---
{request.prompt_text}
---
"""
    generation_config = genai.types.GenerationConfig(response_mime_type="application/json")
    try:
        response = await model.generate_content_async(meta_prompt, generation_config=generation_config)
        llm_result = json.loads(response.text)

        required_keys = ["has_clear_goal", "provides_examples", "specifies_constraints", "provides_context", "is_concise", "diagnosis", "suggested_prompt"]
        if not all(key in llm_result for key in required_keys):
            raise ValueError("LLM response missing required analysis keys.")

        score = 10.0
        if not llm_result.get("has_clear_goal", False): score -= 3.0
        if not llm_result.get("provides_examples", False): score -= 2.0
        if not llm_result.get("specifies_constraints", False): score -= 2.0
        if not llm_result.get("provides_context", False): score -= 1.0
        if not llm_result.get("is_concise", False): score -= 2.0
        
        final_score = round(max(0.0, score), 2)

        key_issues = [k for k, v in llm_result.items() if k in required_keys[:5] and not v]

        return {
            "diagnosis": llm_result["diagnosis"],
            "key_issues": key_issues,
            "suggested_prompt": llm_result["suggested_prompt"],
            "criteria": {
                "clarity": llm_result["has_clear_goal"],
                "specificity": llm_result["provides_examples"],
                "context": llm_result["provides_context"],
                "constraints": llm_result["specifies_constraints"]
            },
            "overall_score": final_score
        }
    except Exception as e:
        logging.error(f"Error diagnosing prompt: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to diagnose prompt: {str(e)}")


async def breakdown_prompt(request: BreakdownRequest) -> dict:
    model = genai.GenerativeModel(DEFAULT_GEMINI_MODEL)
    meta_prompt = f"""
Your primary goal is to analyze the user's prompt and respond with ONLY a single, valid JSON object.
The JSON object must have a single root key called "components", which contains a list of objects.
Each object in the "components" list MUST have exactly three keys: "type", "content", and "explanation".
- "type": Must be one of ["system_role", "instruction", "constraints", "examples", "style_tone", "output_format", "context"].
- "content": Must be the actual text content of that component from the prompt.
- "explanation": A brief explanation of the component's purpose.
Analyze and break down the following prompt:
---
{request.prompt_text}
---
"""
    generation_config = genai.types.GenerationConfig(response_mime_type="application/json")
    try:
        response = await model.generate_content_async(meta_prompt, generation_config=generation_config)
        return json.loads(response.text)
    except Exception as e:
        logging.error(f"Error breaking down prompt: {e}")
        return {"components": [{"type": "error", "content": f"An error occurred: {str(e)}","explanation": "The server failed to process the breakdown request."}]}

async def generate_and_store_template(request: TemplateGenerateRequest) -> dict:
    model = genai.GenerativeModel(DEFAULT_GEMINI_MODEL)
    meta_prompt = f"""
Your task is to generate a complete prompt template object in JSON format based on a user's style description.
You MUST respond with ONLY a single, valid JSON object with these keys: "name", "description", "content", "tags".
The "content" field MUST be a single string, representing the text of the prompt template.
USER'S REQUEST:\nSTYLE DESCRIPTION: "{request.style_description}"\nINITIAL TAGS: {request.tags if request.tags else "None"}
"""
    generation_config = genai.types.GenerationConfig(response_mime_type="application/json")
    try:
        response = await model.generate_content_async(meta_prompt, generation_config=generation_config)
        generated_data = json.loads(response.text)
        generated_tags = generated_data.get("tags", [])
        if request.tags:
            for tag in request.tags:
                if tag not in generated_tags:
                    generated_tags.append(tag)
        generated_data["tags"] = generated_tags
        template_to_create = PromptTemplateCreate(**generated_data)
        created_template = await firestore_service.create_template(template_to_create)
        return created_template
    except Exception as e:
        logging.error(f"Error generating template: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate and store template: {str(e)}")

async def recommend_templates(request: RecommendRequest) -> list[dict]:
    model = genai.GenerativeModel(DEFAULT_GEMINI_MODEL)
    meta_prompt = f"""
Analyze the user's task description and respond with ONLY a single, valid JSON object with one key: "suggested_tags". The value should be a list of 1 to 3 relevant tags.
User's Task: "{request.task_description}"
"""
    generation_config = genai.types.GenerationConfig(response_mime_type="application/json")
    try:
        response = await model.generate_content_async(meta_prompt, generation_config=generation_config)
        suggested_tags = json.loads(response.text).get("suggested_tags", [])
        recommendations = []
        if suggested_tags:
            templates = await firestore_service.list_templates_by_tags(suggested_tags)
            for template in templates:
                recommendations.append({"template": template, "reason": f"Recommended for tag(s): {', '.join(suggested_tags)}."})
        return recommendations
    except Exception as e:
        logging.error(f"Error recommending templates: {e}")
        return []

async def _execute_single_sandbox_run(prompt_input: SandboxPromptInput, common_input: str, model_name: str) -> SandboxResult:
    full_prompt_text = f"{prompt_input.text}\n\n{common_input}" if common_input else prompt_input.text
    benchmark_result = await execute_single_model_benchmark(model_name, full_prompt_text)
    return SandboxResult(prompt_id=prompt_input.id, generated_text=benchmark_result.generated_text, latency_ms=benchmark_result.latency_ms, input_token_count=benchmark_result.input_token_count, output_token_count=benchmark_result.output_token_count)

async def run_sandbox_test(request: SandboxRequest) -> list[SandboxResult]:
    tasks = [_execute_single_sandbox_run(prompt, request.input_text, request.model) for prompt in request.prompts]
    results = await asyncio.gather(*tasks)
    return results
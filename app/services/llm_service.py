import os
import asyncio
import time
import json
from dotenv import load_dotenv

import google.generativeai as genai
from openai import AsyncOpenAI

from app.schemas.prompt import (
    BenchmarkRequest, BenchmarkResult, APEOptimizeRequest, 
    DiagnoseRequest, BreakdownRequest, TemplateGenerateRequest, 
    PromptTemplateCreate, RecommendRequest, SandboxRequest, 
    SandboxResult, SandboxPromptInput
)

from app.services import firestore_service

# --- Constants ---
DEFAULT_GEMINI_MODEL = 'gemini-2.5-flash-lite'

# --- Configuration ---
load_dotenv()

try:
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
except Exception as e:
    print(f"Could not configure Google AI: {e}")

try:
    openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception as e:
    print(f"Could not configure OpenAI: {e}")


# --- Core LLM Call Functions ---

async def _call_gemini(model_name: str, prompt_text: str) -> str:
    """Helper function to call the Gemini API."""
    model = genai.GenerativeModel(model_name)
    response = await model.generate_content_async(prompt_text)
    return response.text

async def _call_openai(model_name: str, prompt_text: str) -> str:
    """Helper function to call the OpenAI API."""
    response = await openai_client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt_text}]
    )
    return response.choices[0].message.content

# --- Main Service Functions ---

async def execute_single_model_benchmark(model_name: str, prompt_text: str) -> BenchmarkResult:
    """Executes and times a single LLM call."""
    start_time = time.perf_counter()
    generated_text = "Error: Model not supported or API key is missing."
    
    try:
        if model_name.startswith("gemini"):
            generated_text = await _call_gemini(model_name, prompt_text)
        elif model_name.startswith("gpt"):
            generated_text = await _call_openai(model_name, prompt_text)
    except Exception as e:
        generated_text = f"Error calling {model_name}: {str(e)}"

    end_time = time.perf_counter()
    latency_ms = (end_time - start_time) * 1000
    
    return BenchmarkResult(
        model_name=model_name,
        generated_text=generated_text,
        latency_ms=latency_ms
    )

async def benchmark_prompt(request: BenchmarkRequest) -> list[BenchmarkResult]:
    """Runs a prompt against a list of models concurrently."""
    tasks = [
        execute_single_model_benchmark(model_name, request.prompt_text) 
        for model_name in request.models
    ]
    results = await asyncio.gather(*tasks)
    return results

async def generate_optimized_prompt(request: APEOptimizeRequest) -> dict:
    """Uses a meta-prompt to generate an optimized prompt and reasoning."""
    model = genai.GenerativeModel(DEFAULT_GEMINI_MODEL)
    formatted_examples = "\n".join(
        [f"INPUT: {ex.input}\nOUTPUT: {ex.output}\n" for ex in request.examples]
    )
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
        print(f"Error optimizing prompt: {e}")
        return {"optimized_prompt": "Error: Could not generate prompt.", "reasoning_summary": str(e)}

async def diagnose_prompt(request: DiagnoseRequest) -> dict:
    """Uses a meta-prompt to diagnose a user's prompt and scores it."""
    model = genai.GenerativeModel(DEFAULT_GEMINI_MODEL)
    meta_prompt = f"""
Your primary task is to act as an expert prompt diagnostician. Analyze the user's prompt and respond with ONLY a single, valid JSON object.
The JSON object must contain these keys: "diagnosis", "key_issues", "suggested_prompt", and "criteria".
The "criteria" object must contain these four keys, each with a float score from 0.0 to 10.0: "clarity", "specificity", "context", "constraints".
Do NOT include an "overall_score" in your JSON response.
Analyze this prompt:\n---\n{request.prompt_text}\n---
"""
    generation_config = genai.types.GenerationConfig(response_mime_type="application/json")
    try:
        response = await model.generate_content_async(meta_prompt, generation_config=generation_config)
        llm_result = json.loads(response.text)
        criteria_scores = llm_result.get("criteria", {})
        if criteria_scores:
            total_score = sum(criteria_scores.values())
            num_scores = len(criteria_scores)
            average_score = total_score / num_scores if num_scores > 0 else 0.0
            llm_result["overall_score"] = round(average_score, 2)
        else:
            llm_result["overall_score"] = 0.0
        return llm_result
    except Exception as e:
        print(f"Error diagnosing prompt: {e}")
        return {
            "overall_score": 0.0, "diagnosis": "Failed to analyze prompt.", "key_issues": [str(e)],
            "suggested_prompt": "N/A", "criteria": {"clarity": 0.0, "specificity": 0.0, "context": 0.0, "constraints": 0.0}
        }

async def breakdown_prompt(request: BreakdownRequest) -> dict:
    """
    Uses a meta-prompt and Gemini's JSON Mode to break down a prompt.
    """
    model = genai.GenerativeModel('gemini-2.5-flash-lite')

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
    
    generation_config = genai.types.GenerationConfig(
        response_mime_type="application/json"
    )

    try:
        response = await model.generate_content_async(
            meta_prompt,
            generation_config=generation_config
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"Error breaking down prompt: {e}")
        return {
            "components": [
                {
                    "type": "error",
                    "content": f"An error occurred: {str(e)}",
                    "explanation": "The server failed to process the breakdown request."
                }
            ]
        }

async def generate_and_store_template(request: TemplateGenerateRequest) -> dict:
    """Uses an LLM to generate a new PromptTemplate and saves it to Firestore."""
    model = genai.GenerativeModel(DEFAULT_GEMINI_MODEL)
    meta_prompt = f"""
Your task is to generate a complete prompt template object in JSON format based on a user's style description.
You MUST respond with ONLY a single, valid JSON object with these keys: "name", "description", "content", "tags".
USER'S REQUEST:\nSTYLE DESCRIPTION: "{request.style_description}"\nINITIAL TAGS: {request.tags if request.tags else "None"}
"""
    generation_config = genai.types.GenerationConfig(response_mime_type="application/json")
    try:
        response = await model.generate_content_async(meta_prompt, generation_config=generation_config)
        generated_data = json.loads(response.text)
        template_to_create = PromptTemplateCreate(**generated_data)
        created_template = await firestore_service.create_template(template_to_create)
        return created_template
    except Exception as e:
        print(f"Error generating template: {e}")
        raise e

async def recommend_templates(request: RecommendRequest) -> list[dict]:
    """Uses an LLM to recommend templates based on a task description."""
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
                recommendations.append({
                    "template": template,
                    "reason": f"Recommended for tag(s): {', '.join(suggested_tags)}."
                })
        return recommendations
    except Exception as e:
        print(f"Error recommending templates: {e}")
        return []

async def _execute_single_sandbox_run(prompt_input: SandboxPromptInput, common_input: str, model_name: str) -> SandboxResult:
    full_prompt_text = f"{prompt_input.text}\n\n{common_input}" if common_input else prompt_input.text
    # We call the main benchmark helper here
    benchmark_result = await execute_single_model_benchmark(model_name, full_prompt_text)
    
    return SandboxResult(
        prompt_id=prompt_input.id,
        generated_text=benchmark_result.generated_text,
        latency_ms=benchmark_result.latency_ms
    )

async def run_sandbox_test(request: SandboxRequest) -> list[SandboxResult]:
    """Runs an A/B test on a list of prompts concurrently."""
    tasks = [
        _execute_single_sandbox_run(prompt, request.input_text, request.model)
        for prompt in request.prompts
    ]
    results = await asyncio.gather(*tasks)
    return results
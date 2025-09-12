import os
import asyncio
import time
from dotenv import load_dotenv

import google.generativeai as genai
from openai import AsyncOpenAI

from app.schemas.prompt import BenchmarkRequest, BenchmarkResult

# Load environment variables
load_dotenv()

# Configure Google Gemini client
try:
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
except Exception as e:
    print(f"Could not configure Google AI: {e}")

# Configure OpenAI client
try:
    openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception as e:
    print(f"Could not configure OpenAI: {e}")


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
    """
    Runs a prompt against a list of models concurrently and returns their performance.
    """
    tasks = [
        execute_single_model_benchmark(model_name, request.prompt_text) 
        for model_name in request.models
    ]
    
    results = await asyncio.gather(*tasks)
    return results
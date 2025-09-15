# test_api.py
import requests
import json
import sys
import time
import os

BASE_URL = "http://127.0.0.1:8000"
HEADERS = {"Content-Type": "application/json", "accept": "application/json"}
DEFAULT_MODEL = "gemini-1.5-pro-latest"

def run_test(name, method, url, payload=None, expected_status=200):
    """Helper function to run a test and print the results."""
    print(f"--- Testing: {name} ---")
    try:
        response = requests.request(method.upper(), url, headers=HEADERS, data=json.dumps(payload) if payload else None)
        print(f"Status Code: {response.status_code}")
        assert response.status_code == expected_status, f"Expected status {expected_status}, but got {response.status_code}"

        if response.status_code != 204:
            response_json = response.json()
            print("Response JSON:")
            print(json.dumps(response_json, indent=2))
            return response_json
        else:
            print("Success (No Content)")
            return None
            
    except (requests.exceptions.RequestException, AssertionError, json.JSONDecodeError) as e:
        print(f"!!! TEST FAILED: {name} - {type(e).__name__}: {e} !!!")
        if 'response' in locals() and response.text:
            print(f"Error Body: {response.text}")
        sys.exit(1)
    finally:
        print("-" * 30 + "\n")

def test_prompt_lifecycle():
    print("\n" + "="*10 + " TESTING PROMPT LIFECYCLE " + "="*10 + "\n")
    create_payload = {
        "name": f"Test Lifecycle Prompt {int(time.time())}", 
        "task_description": "A test prompt from the script.", 
        "initial_prompt_text": "This is version 1."
    }
    created_prompt = run_test("Create Prompt", "POST", f"{BASE_URL}/prompts/", create_payload, expected_status=201)
    prompt_id = created_prompt["id"]
    
    run_test("Get Single Prompt", "GET", f"{BASE_URL}/prompts/{prompt_id}")
    run_test("Update Prompt", "PATCH", f"{BASE_URL}/prompts/{prompt_id}", payload={"name": "Updated Test Prompt"})
    run_test("Create New Version", "POST", f"{BASE_URL}/prompts/{prompt_id}/versions", payload={"prompt_text": "This is v2.", "commit_message": "v2 test"}, expected_status=201)
    run_test("List All Versions", "GET", f"{BASE_URL}/prompts/{prompt_id}/versions")
    
    return prompt_id

def test_ai_features():
    print("\n" + "="*10 + " TESTING AI FEATURES " + "="*10 + "\n")
    
    # Test Execute Endpoint
    execute_payload = {
        "prompt_text": "Summarize Hamlet in one sentence.",
        "model": DEFAULT_MODEL,
        "variables": {}
    }
    response = run_test("Execute Prompt", "POST", f"{BASE_URL}/prompts/execute", payload=execute_payload)
    assert "final_text" in response and response["final_text"]
    assert "cost" in response and isinstance(response["cost"], float)
    assert "latency_ms" in response and response["latency_ms"] > 0
    print("   ✅ Verified Execute response structure and metrics.")

    # Test Benchmark Endpoint
    benchmark_payload = {
        "prompt_text": "What are the key differences between Python and JavaScript?",
        "models": [DEFAULT_MODEL]
    }
    response = run_test("Run Model Benchmark", "POST", f"{BASE_URL}/prompts/benchmark", payload=benchmark_payload)
    assert "results" in response and len(response["results"]) > 0
    first_result = response["results"][0]
    assert "final_text" in first_result and first_result["final_text"]
    assert "cost" in first_result
    print("   ✅ Verified Benchmark response structure.")

    # Test Diagnose Endpoint
    diagnose_payload = {"prompt_text": "write code for me"}
    response = run_test("Diagnose Prompt", "POST", f"{BASE_URL}/prompts/diagnose", payload=diagnose_payload)
    assert "overall_score" in response and "suggested_prompt" in response
    assert "criteria" in response and "clarity" in response["criteria"]
    print("   ✅ Verified Diagnose response structure.")

    # Test Breakdown Endpoint
    breakdown_payload = {"prompt_text": "You are a helpful assistant. Please summarize this text."}
    response = run_test("Breakdown Prompt", "POST", f"{BASE_URL}/prompts/breakdown", payload=breakdown_payload)
    assert "components" in response and len(response["components"]) > 0
    print("   ✅ Verified Breakdown response structure.")
    
    # Test Optimize (APE) Endpoint
    optimize_payload = {
        "task_description": "Turn a statement into a question.",
        "examples": [{"input": "It is sunny.", "output": "Is it sunny?"}]
    }
    response = run_test("Optimize Prompt (APE)", "POST", f"{BASE_URL}/prompts/optimize", payload=optimize_payload)
    assert "optimized_prompt" in response and "reasoning_summary" in response
    print("   ✅ Verified Optimize (APE) response structure.")


def cleanup(prompt_id):
    print("\n" + "="*10 + " CLEANING UP " + "="*10 + "\n")
    if prompt_id:
        run_test(f"Delete Prompt {prompt_id}", "DELETE", f"{BASE_URL}/prompts/{prompt_id}", expected_status=204)

if __name__ == "__main__":
    prompt_to_delete = None
    try:
        prompt_to_delete = test_prompt_lifecycle()
        test_ai_features() # Run the full suite of AI tests
    finally:
        cleanup(prompt_to_delete)
        print("\n" + "="*20 + " TEST SUITE COMPLETE " + "="*20 + "\n")
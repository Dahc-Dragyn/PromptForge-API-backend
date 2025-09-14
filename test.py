import requests
import json
import sys
import math
import time
import os

BASE_URL = "http://127.0.0.1:8000"
HEADERS = {"Content-Type": "application/json", "accept": "application/json"}

# --- MODIFIED BLOCK: Updated run_test helper ---
def run_test(name, method, url, payload=None, expected_status=None):
    """Helper function to run a test and print the results."""
    print(f"--- Testing: {name} ---")
    try:
        if method.upper() == 'GET':
            response = requests.get(url, headers=HEADERS)
        elif method.upper() == 'POST':
            response = requests.post(url, headers=HEADERS, data=json.dumps(payload))
        elif method.upper() == 'PATCH':
            response = requests.patch(url, headers=HEADERS, data=json.dumps(payload))
        elif method.upper() == 'DELETE':
            response = requests.delete(url, headers=HEADERS)
        else:
            raise ValueError(f"Unsupported method: {method}")

        print(f"Status Code: {response.status_code}")
        
        # If an expected status is provided, check against it
        if expected_status:
            assert response.status_code == expected_status, f"Expected status {expected_status}, but got {response.status_code}"
        # Otherwise, use default success codes
        else:
            response.raise_for_status()

        if response.status_code != 204:
            response_json = response.json()
            print("Response JSON:")
            print(json.dumps(response_json, indent=2))
            return response_json
        else:
            print("Success (No Content)")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"!!! TEST FAILED: {name} - {e} !!!")
        if 'response' in locals() and response.text:
            print(f"Error Body: {response.text}")
        sys.exit(1)
    except AssertionError as e:
        print(f"!!! ASSERTION FAILED: {e} !!!")
        sys.exit(1)
    finally:
        print("-" * 30 + "\n")


def test_prompt_lifecycle():
    print("\n" + "="*10 + " TESTING PROMPT LIFECYCLE " + "="*10 + "\n")
    create_payload = {"name": "Test Script Prompt", "task_description": "A test prompt.", "initial_prompt_text": "Version 1."}
    created_prompt = run_test("Create Prompt", "POST", f"{BASE_URL}/prompts/", create_payload)
    prompt_id = created_prompt["id"]
    run_test("List Prompts", "GET", f"{BASE_URL}/prompts/")
    run_test("Get Single Prompt", "GET", f"{BASE_URL}/prompts/{prompt_id}")
    run_test("Update Prompt", "PATCH", f"{BASE_URL}/prompts/{prompt_id}", payload={"name": "Test Script Prompt (UPDATED)"})
    run_test("Create New Version", "POST", f"{BASE_URL}/prompts/{prompt_id}/versions", payload={"prompt_text": "This is v2.", "commit_message": "v2 test"})
    run_test("List All Versions", "GET", f"{BASE_URL}/prompts/{prompt_id}/versions")
    return prompt_id

def test_template_library():
    print("\n" + "="*10 + " TESTING TEMPLATE LIBRARY " + "="*10 + "\n")
    unique_suffix = str(int(time.time()))
    run_test("Create Template 1 (Task)", "POST", f"{BASE_URL}/templates/", payload={"name": f"Test Task: Summarize {unique_suffix}", "description": "A test task.", "content": "Summarize: {text}", "tags": ["summarize", "test_script"]})
    run_test("Create Template 2 (Persona)", "POST", f"{BASE_URL}/templates/", payload={"name": f"Test Persona: Pirate {unique_suffix}", "description": "A test persona.", "content": "You are a pirate.", "tags": ["persona", "pirate", "test_script"]})
    run_test("List All Templates", "GET", f"{BASE_URL}/templates/")
    run_test("Filter Templates by Tag", "GET", f"{BASE_URL}/templates/?tag=pirate")
    run_test("AI Generate Template", "POST", f"{BASE_URL}/templates/generate", payload={"style_description": f"A persona for a fitness coach named Coach {unique_suffix}", "tags": ["persona", "fitness", "test_script"]})
    run_test("Compose Prompt", "POST", f"{BASE_URL}/templates/compose", payload={"persona": "pirate", "task": "summarize"})
    run_test("Recommend Template", "POST", f"{BASE_URL}/templates/recommend", payload={"task_description": "I need to write a professional email."})

def test_ai_features():
    print("\n" + "="*10 + " TESTING AI FEATURES " + "="*10 + "\n")
    execute_response = run_test("Execute Prompt (Platform Key)", "POST", f"{BASE_URL}/prompts/execute", payload={"prompt_text": "Summarize Hamlet in one sentence."})
    if execute_response:
        assert "input_token_count" in execute_response and execute_response["input_token_count"] > 0
        assert "output_token_count" in execute_response and execute_response["output_token_count"] > 0
        print("   ✅ Input/Output token counts verified for Execute.")

    run_test("Optimize Prompt (APE)", "POST", f"{BASE_URL}/prompts/optimize", payload={"task_description": "Turn a statement into a question.", "examples": [{"input": "It is sunny.", "output": "Is it sunny?"}]})
    
    benchmark_response = run_test("Benchmark Prompt", "POST", f"{BASE_URL}/prompts/benchmark", payload={"prompt_text": "Differences between Python and JS?", "models": ["gemini-2.5-flash-lite"]})
    if benchmark_response and "results" in benchmark_response:
        for result in benchmark_response["results"]:
            assert "input_token_count" in result and result["input_token_count"] > 0
            assert "output_token_count" in result and result["output_token_count"] > 0
            print(f"   -> Verified I/O tokens for {result['model_name']}: {result['input_token_count']}/{result['output_token_count']}")
        print("   ✅ Input/Output token count verification successful for Benchmark.")

    diagnose_response = run_test("Diagnose Prompt", "POST", f"{BASE_URL}/prompts/diagnose", payload={"prompt_text": "write code"})
    if diagnose_response:
        assert "overall_score" in diagnose_response and isinstance(diagnose_response["overall_score"], (int, float))
        assert "criteria" in diagnose_response
        criteria = diagnose_response["criteria"]
        assert isinstance(criteria.get("clarity"), bool)
        assert isinstance(criteria.get("specificity"), bool)
        print("   ✅ Deterministic diagnosis response verified.")

    run_test("Breakdown Prompt", "POST", f"{BASE_URL}/prompts/breakdown", payload={"prompt_text": "You are a helpful assistant. Summarize."})

    sandbox_response = run_test("A/B Test Sandbox", "POST", f"{BASE_URL}/sandbox/", payload={"prompts": [{"id": "v1", "text": "What is a CPU?"}, {"id": "v2", "text": "Explain a CPU to a student."}], "input_text": "", "model": "gemini-2.5-flash-lite"})
    if sandbox_response and "results" in sandbox_response:
        for result in sandbox_response["results"]:
            assert "input_token_count" in result and result["input_token_count"] > 0
            assert "output_token_count" in result and result["output_token_count"] > 0
            print(f"   -> Verified I/O tokens for {result['prompt_id']}: {result['input_token_count']}/{result['output_token_count']}")
        print("   ✅ Input/Output token count verification successful for Sandbox.")

# --- NEW TEST FUNCTION ---
def test_execution_features():
    print("\n" + "="*10 + " TESTING EXECUTION FEATURES " + "="*10 + "\n")
    
    test_user_id = "test_user_123"
    
    # Securely get the API key from environment variables
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("--- SKIPPING EXECUTION TESTS: OPENAI_API_KEY not found in environment variables. ---")
        return

    # 1. Save the user's API key
    key_payload = {"provider": "openai", "api_key": openai_api_key}
    run_test("Save User API Key", "POST", f"{BASE_URL}/users/{test_user_id}/keys", payload=key_payload, expected_status=204)

    # 2. Run a managed execution (Success Case)
    exec_payload = {
        "user_id": test_user_id,
        "model_name": "gpt-4o-mini",
        "prompt_text": "What is the capital of Washington state?"
    }
    response = run_test("Managed Execution (Success)", "POST", f"{BASE_URL}/execute/managed", payload=exec_payload, expected_status=200)
    if response:
        assert "generated_text" in response
        assert "Olympia" in response["generated_text"]
        assert response["input_token_count"] > 0
        assert response["output_token_count"] > 0
        print("   ✅ Managed execution successful with valid response and metrics.")

    # 3. Run a managed execution with a non-existent user (Failure Case)
    fail_payload = {
        "user_id": "non_existent_user_456",
        "model_name": "gpt-4o-mini",
        "prompt_text": "This should fail."
    }
    run_test("Managed Execution (Failure - No Key)", "POST", f"{BASE_URL}/execute/managed", payload=fail_payload, expected_status=403)
    print("   ✅ Managed execution correctly failed for a user with no key.")


def test_metrics_features():
    print("\n" + "="*10 + " TESTING METRICS FEATURES " + "="*10 + "\n")
    
    summary_response = run_test("Get Prompts Summary", "GET", f"{BASE_URL}/metrics/summary")
    if summary_response and "results" in summary_response:
        assert isinstance(summary_response["results"], list)
        print("   ✅ Verified 'results' key is a list.")
        if summary_response["results"]:
            first_prompt = summary_response["results"][0]
            assert "id" in first_prompt
            assert "name" in first_prompt
            assert "version_count" in first_prompt
            assert "average_rating" in first_prompt
            assert "rating_count" in first_prompt
            print("   ✅ Verified structure of the first prompt summary object.")

    cost_payload = {
        "model_name": "gemini-2.5-flash-lite",
        "input_token_count": 10000,
        "output_token_count": 5000
    }
    response = run_test("Calculate Accurate Cost", "POST", f"{BASE_URL}/metrics/calculate-cost", cost_payload)
    
    price_per_million_input = 0.35
    price_per_million_output = 0.70
    expected_cost = ((10000 / 1_000_000) * price_per_million_input) + ((5000 / 1_000_000) * price_per_million_output)
    actual_cost = response.get("estimated_cost_usd")
    assert math.isclose(actual_cost, expected_cost), f"!!! COST VERIFICATION FAILED: Expected {expected_cost}, but got {actual_cost} !!!"
    print(f"   -> Verified accurate cost calculation: ${actual_cost}")
    print("   ✅ Accurate cost calculation verification successful.")

def cleanup(prompt_id):
    print("\n" + "="*10 + " CLEANING UP TEST RESOURCES " + "="*10 + "\n")
    if prompt_id:
        run_test(f"Delete Prompt {prompt_id}", "DELETE", f"{BASE_URL}/prompts/{prompt_id}", expected_status=204)
    templates = run_test("List All Templates for Cleanup", "GET", f"{BASE_URL}/templates/?tag=test_script")
    if templates:
        for t in templates:
            run_test(f"Delete Template '{t['name']}'", "DELETE", f"{BASE_URL}/templates/{t['id']}", expected_status=204)

if __name__ == "__main__":
    prompt_to_delete = None
    try:
        prompt_to_delete = test_prompt_lifecycle()
        test_template_library()
        test_ai_features()
        test_metrics_features()
        # --- NEW LINE ---
        test_execution_features()
    finally:
        cleanup(prompt_to_delete)
        print("\n" + "="*10 + " TEST SUITE COMPLETE " + "="*10 + "\n")
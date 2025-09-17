# test_master.py
import requests
import json
import sys
import time
import os
import math
# --- FIX: Import and load the .env file ---
from dotenv import load_dotenv
load_dotenv()

# --- Configuration ---
BASE_URL = "http://127.0.0.1:8000"
HEADERS = {"Content-Type": "application/json", "accept": "application/json"}
# Use a model that is likely to be configured with the platform key
DEFAULT_GEMINI_MODEL = "gemini-1.5-flash-latest" 
# A model for testing user-specific keys (OpenAI in this case)
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
TEST_USER_ID = "test_suite_user_12345"

# --- Helper Function (Unchanged) ---
def run_test(name, method, url, payload=None, expected_status=None):
    """Helper function to run a test and print comprehensive results."""
    print(f"--- Testing: {name} ---")
    try:
        response = requests.request(method.upper(), url, headers=HEADERS, data=json.dumps(payload) if payload else None)

        print(f"URL: {method.upper()} {url}")
        print(f"Status Code: {response.status_code}")

        if expected_status:
            assert response.status_code == expected_status, f"Expected status {expected_status}, but got {response.status_code}"
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

    except (requests.exceptions.RequestException, AssertionError, json.JSONDecodeError) as e:
        print(f"!!! TEST FAILED: {name} - {type(e).__name__}: {e} !!!")
        if 'response' in locals() and response.text:
            print(f"Error Body: {response.text}")
        sys.exit(1)
    finally:
        print("-" * 40 + "\n")

# --- Test Functions (All Unchanged) ---

def test_health_check():
    print("\n" + "="*10 + " TESTING HEALTH CHECK " + "="*10 + "\n")
    run_test("Health Check", "GET", f"{BASE_URL}/")

def test_prompt_endpoints():
    print("\n" + "="*10 + " TESTING PROMPT & VERSIONING ENDPOINTS " + "="*10 + "\n")
    create_payload = {"name": f"Test Prompt {int(time.time())}", "task_description": "A test prompt.", "initial_prompt_text": "This is version 1."}
    created_prompt = run_test("Create Prompt", "POST", f"{BASE_URL}/prompts/", create_payload, expected_status=201)
    prompt_id = created_prompt["id"]
    run_test("List All Prompts", "GET", f"{BASE_URL}/prompts/")
    run_test("Get Single Prompt", "GET", f"{BASE_URL}/prompts/{prompt_id}")
    run_test("Update Prompt", "PATCH", f"{BASE_URL}/prompts/{prompt_id}", payload={"name": "Updated Test Prompt Name"})
    run_test("Create New Version", "POST", f"{BASE_URL}/prompts/{prompt_id}/versions", payload={"prompt_text": "This is v2.", "commit_message": "v2 test"}, expected_status=201)
    run_test("List All Versions", "GET", f"{BASE_URL}/prompts/{prompt_id}/versions")
    return prompt_id

def test_ai_and_analysis_endpoints():
    print("\n" + "="*10 + " TESTING AI & ANALYSIS ENDPOINTS " + "="*10 + "\n")
    execute_payload = {"prompt_text": "Summarize the plot of Hamlet in one sentence.", "model": DEFAULT_GEMINI_MODEL, "variables": {}}
    response = run_test("Execute Prompt (Platform Key)", "POST", f"{BASE_URL}/prompts/execute", payload=execute_payload)
    assert "final_text" in response and response["final_text"]
    assert "cost" in response and isinstance(response["cost"], float) and response["cost"] >= 0
    print("   ✅ Verified Execute (Platform Key) response structure.")
    run_test("Optimize Prompt (APE)", "POST", f"{BASE_URL}/prompts/optimize", payload={"task_description": "Turn a statement into a question.", "examples": [{"input": "It is sunny.", "output": "Is it sunny?"}]})
    run_test("Benchmark Prompt", "POST", f"{BASE_URL}/prompts/benchmark", payload={"prompt_text": "Differences between Python and JS?", "models": [DEFAULT_GEMINI_MODEL]})
    run_test("Diagnose Prompt", "POST", f"{BASE_URL}/prompts/diagnose", payload={"prompt_text": "write code"})
    run_test("Breakdown Prompt", "POST", f"{BASE_URL}/prompts/breakdown", payload={"prompt_text": "You are a helpful assistant. Summarize this text."})

def test_template_endpoints():
    print("\n" + "="*10 + " TESTING TEMPLATE ENDPOINTS " + "="*10 + "\n")
    unique_suffix = str(int(time.time()))
    template_payload = {"name": f"Test Persona: Pirate {unique_suffix}", "description": "A test persona.", "content": "You are a pirate who loves treasure.", "tags": ["persona", "pirate", "test_script"]}
    created_template = run_test("Create Template", "POST", f"{BASE_URL}/templates/", template_payload, expected_status=201)
    template_id = created_template["id"]
    run_test("List All Templates", "GET", f"{BASE_URL}/templates/")
    run_test("Filter Templates by Tag", "GET", f"{BASE_URL}/templates/?tag=pirate")
    run_test("AI Generate Template", "POST", f"{BASE_URL}/templates/generate", payload={"style_description": f"A persona for a chef named Chef {unique_suffix}", "tags": ["persona", "chef", "test_script"]}, expected_status=201)
    run_test("Compose Prompt", "POST", f"{BASE_URL}/templates/compose", payload={"persona": "pirate", "task": "summarize"})
    run_test("Recommend Template", "POST", f"{BASE_URL}/templates/recommend", payload={"task_description": "I need to write a professional email."})
    return template_id

def test_sandbox_endpoints():
    print("\n" + "="*10 + " TESTING SANDBOX ENDPOINTS " + "="*10 + "\n")
    run_test("A/B Test Sandbox", "POST", f"{BASE_URL}/sandbox/", payload={"prompts": [{"id": "v1", "text": "What is a CPU?"}, {"id": "v2", "text": "Explain a CPU to a 5th grader."}], "input_text": "", "model": DEFAULT_GEMINI_MODEL})

def test_metrics_endpoints():
    print("\n" + "="*10 + " TESTING METRICS ENDPOINTS " + "="*10 + "\n")
    run_test("Get Prompts Summary", "GET", f"{BASE_URL}/metrics/summary")
    cost_payload = {"model_name": "gemini-1.5-flash-latest", "input_token_count": 10000, "output_token_count": 5000}
    run_test("Calculate Cost", "POST", f"{BASE_URL}/metrics/calculate-cost", payload=cost_payload)

def test_user_and_execution_endpoints():
    print("\n" + "="*10 + " TESTING USER & MANAGED EXECUTION " + "="*10 + "\n")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("--- SKIPPING MANAGED EXECUTION TESTS: OPENAI_API_KEY not found in environment variables. ---")
        return

    key_payload = {"provider": "openai", "api_key": openai_api_key}
    run_test("Save User API Key", "POST", f"{BASE_URL}/users/{TEST_USER_ID}/keys", payload=key_payload, expected_status=204)
    exec_payload = {"user_id": TEST_USER_ID, "model_name": DEFAULT_OPENAI_MODEL, "prompt_text": "What is the capital of Oregon?"}
    response = run_test("Managed Execution (Success)", "POST", f"{BASE_URL}/users/execute", payload=exec_payload)
    assert "Salem" in response.get("final_text", "")
    print("   ✅ Managed execution successful.")
    fail_payload = {"user_id": "non-existent-user", "model_name": DEFAULT_OPENAI_MODEL, "prompt_text": "This should fail."}
    run_test("Managed Execution (Failure - No Key)", "POST", f"{BASE_URL}/users/execute", payload=fail_payload, expected_status=403)
    print("   ✅ Managed execution correctly failed for a user with no key.")

def cleanup(prompt_id, template_id):
    print("\n" + "="*10 + " CLEANING UP TEST RESOURCES " + "="*10 + "\n")
    if prompt_id:
        run_test(f"Delete Prompt {prompt_id}", "DELETE", f"{BASE_URL}/prompts/{prompt_id}", expected_status=204)
    templates = run_test("List All Templates for Cleanup", "GET", f"{BASE_URL}/templates/?tag=test_script")
    if templates:
        for t in templates:
            run_test(f"Delete Template '{t['name']}'", "DELETE", f"{BASE_URL}/templates/{t['id']}", expected_status=204)


if __name__ == "__main__":
    prompt_id_to_delete = None
    template_id_to_delete = None
    try:
        test_health_check()
        prompt_id_to_delete = test_prompt_endpoints()
        test_ai_and_analysis_endpoints()
        template_id_to_delete = test_template_endpoints()
        test_sandbox_endpoints()
        test_metrics_endpoints()
        test_user_and_execution_endpoints()
    finally:
        cleanup(prompt_id_to_delete, template_id_to_delete)
        print("\n" + "="*20 + " TEST SUITE COMPLETE " + "="*20 + "\n")
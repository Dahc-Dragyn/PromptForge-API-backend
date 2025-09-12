import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8000"
HEADERS = {"Content-Type": "application/json", "accept": "application/json"}

def run_test(name, method, url, payload=None):
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
        response.raise_for_status()
        
        if response.status_code != 204:
            print("Response JSON:")
            print(json.dumps(response.json(), indent=2))
            return response.json()
        else:
            print("Success (No Content)")
            return None
    except requests.exceptions.RequestException as e:
        print(f"!!! TEST FAILED: {name} - {e} !!!")
        if 'response' in locals() and response.text:
            print(f"Error Body: {response.text}")
        sys.exit(1) # Exit script on failure
    finally:
        print("-" * 30 + "\n")

def test_prompt_lifecycle():
    print("\n" + "="*10 + " TESTING PROMPT LIFECYCLE " + "="*10 + "\n")
    create_payload = {
        "name": "Test Script Prompt",
        "task_description": "A prompt created by the integration test script.",
        "initial_prompt_text": "This is version 1 of the test prompt."
    }
    created_prompt = run_test("Create Prompt", "POST", f"{BASE_URL}/prompts/", create_payload)
    
    if not created_prompt:
        print("!!! CRITICAL FAILURE: Could not create prompt, aborting. !!!")
        return None
        
    prompt_id = created_prompt["id"]
    run_test("List Prompts", "GET", f"{BASE_URL}/prompts/")
    run_test("Get Single Prompt", "GET", f"{BASE_URL}/prompts/{prompt_id}")
    update_payload = {"name": "Test Script Prompt (UPDATED)"}
    run_test("Update Prompt", "PATCH", f"{BASE_URL}/prompts/{prompt_id}", update_payload)
    version2_payload = {
        "prompt_text": "This is version 2, with a commit message.",
        "commit_message": "v2: Test script adding a new version."
    }
    run_test("Create New Version", "POST", f"{BASE_URL}/prompts/{prompt_id}/versions", version2_payload)
    run_test("List All Versions", "GET", f"{BASE_URL}/prompts/{prompt_id}/versions")
    
    return prompt_id

def test_template_library():
    print("\n" + "="*10 + " TESTING TEMPLATE LIBRARY " + "="*10 + "\n")
    # Create templates with unique names to ensure re-runnability
    template1 = run_test(
        "Create Template 1 (Task)", "POST", f"{BASE_URL}/templates/",
        payload={"name": "Test Script Task: Summarize", "description": "A test task.", "content": "Summarize this: {text}", "tags": ["summarize", "test_script"]}
    )
    template2 = run_test(
        "Create Template 2 (Persona)", "POST", f"{BASE_URL}/templates/",
        payload={"name": "Test Script Persona: Pirate", "description": "A test persona.", "content": "You are a pirate.", "tags": ["persona", "pirate", "test_script"]}
    )
    
    run_test("List All Templates", "GET", f"{BASE_URL}/templates/")
    run_test("Filter Templates by Tag", "GET", f"{BASE_URL}/templates/?tag=pirate")

    generate_payload = {
        "style_description": "A persona for a cheerful and encouraging fitness coach.",
        "tags": ["persona", "fitness", "test_script"]
    }
    run_test("AI Generate Template", "POST", f"{BASE_URL}/templates/generate", generate_payload)

    compose_payload = {"persona": "pirate", "task": "summarize"}
    run_test("Compose Prompt", "POST", f"{BASE_URL}/templates/compose", compose_payload)

    recommend_payload = {"task_description": "I need to write a professional email about a project delay."}
    run_test("Recommend Template", "POST", f"{BASE_URL}/templates/recommend", recommend_payload)


def test_ai_features():
    print("\n" + "="*10 + " TESTING AI FEATURES " + "="*10 + "\n")
    execute_payload = {"prompt_text": "Write a one-sentence summary of Hamlet."}
    run_test("Execute Prompt", "POST", f"{BASE_URL}/prompts/execute", execute_payload)

    optimize_payload = {
        "task_description": "Turn a statement into a question.",
        "examples": [{"input": "The server is online.", "output": "Is the server online?"}]
    }
    run_test("Optimize Prompt (APE)", "POST", f"{BASE_URL}/prompts/optimize", optimize_payload)

    benchmark_payload = {
        "prompt_text": "What are the main differences between Python and JavaScript?",
        "models": ["gemini-2.5-flash-lite", "gpt-4.1-nano"]
    }
    run_test("Benchmark Prompt", "POST", f"{BASE_URL}/prompts/benchmark", benchmark_payload)
    
    diagnose_payload = {"prompt_text": "write code"}
    run_test("Diagnose Prompt", "POST", f"{BASE_URL}/prompts/diagnose", diagnose_payload)
    
    breakdown_payload = {
        "prompt_text": "You are a helpful assistant. Summarize the user's text in 3 bullet points. The tone must be professional. Text: {user_text}"
    }
    run_test("Breakdown Prompt", "POST", f"{BASE_URL}/prompts/breakdown", breakdown_payload)

    sandbox_payload = {
        "prompts": [
            {"id": "v1", "text": "What is a CPU?"},
            {"id": "v2", "text": "You are a computer science professor. Explain a CPU to a first-year student."}
        ],
        "input_text": "",
        "model": "gemini-2.5-flash-lite"
    }
    run_test("A/B Test Sandbox", "POST", f"{BASE_URL}/sandbox/", sandbox_payload)

def cleanup(prompt_id):
    print("\n" + "="*10 + " CLEANING UP TEST RESOURCES " + "="*10 + "\n")
    if prompt_id:
        run_test(f"Delete Prompt {prompt_id}", "DELETE", f"{BASE_URL}/prompts/{prompt_id}")
    
    # Clean up all templates created by the script for re-runnability
    templates = run_test("List All Templates for Cleanup", "GET", f"{BASE_URL}/templates/?tag=test_script")
    if templates:
        for t in templates:
            run_test(f"Delete Template '{t['name']}'", "DELETE", f"{BASE_URL}/templates/{t['id']}")

if __name__ == "__main__":
    prompt_to_delete = None
    try:
        prompt_to_delete = test_prompt_lifecycle()
        test_template_library()
        test_ai_features()
    finally:
        cleanup(prompt_to_delete)
        print("\n" + "="*10 + " TEST SUITE COMPLETE " + "="*10 + "\n")
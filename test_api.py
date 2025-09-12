import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def run_test(name, method, url, payload=None):
    """Helper function to run a test and print the results."""
    print(f"--- Testing: {name} ---")
    headers = {"Content-Type": "application/json", "accept": "application/json"}
    
    try:
        if method.upper() == 'GET':
            response = requests.get(url, headers=headers)
        elif method.upper() == 'POST':
            response = requests.post(url, headers=headers, data=json.dumps(payload))
        elif method.upper() == 'PATCH':
            response = requests.patch(url, headers=headers, data=json.dumps(payload))
        elif method.upper() == 'DELETE':
            response = requests.delete(url, headers=headers)
        else:
            print(f"Unsupported method: {method}")
            return None

        print(f"Status Code: {response.status_code}")
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        
        if response.status_code != 204: # 204 No Content has no body
            print("Response JSON:")
            print(json.dumps(response.json(), indent=2))
            return response.json()
        else:
            print("Success (No Content)")
            return None

    except requests.exceptions.RequestException as e:
        print(f"!!! TEST FAILED: {e} !!!")
        if 'response' in locals() and response.text:
            print(f"Error Body: {response.text}")
        return None
    finally:
        print("-" * 30 + "\n")


if __name__ == "__main__":
    # --- Test 1: Health Check ---
    run_test("Health Check", "GET", f"{BASE_URL}/")

    # --- Test 2: Create a new prompt ---
    create_payload = {
        "name": "Test Script Prompt",
        "task_description": "A prompt created by the integration test script.",
        "initial_prompt_text": "This is version 1 of the test prompt."
    }
    created_prompt = run_test("Create Prompt", "POST", f"{BASE_URL}/prompts/", create_payload)
    
    if created_prompt:
        prompt_id = created_prompt["id"]

        # --- Test 3-7: Full CRUD and Versioning Lifecycle ---
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

        # --- Test 8 & 9: Deletion and Verification ---
        run_test("Delete Prompt", "DELETE", f"{BASE_URL}/prompts/{prompt_id}")
        print("--- Verifying Deletion (expecting 404) ---")
        verify_response = requests.get(f"{BASE_URL}/prompts/{prompt_id}")
        if verify_response.status_code == 404:
            print("Status Code: 404")
            print("Success: Prompt correctly deleted.")
        else:
            print(f"!!! VERIFICATION FAILED: Expected 404 but got {verify_response.status_code} !!!")
        print("-" * 30 + "\n")

    # --- Test 10-14: LLM and Analysis Endpoints ---
    execute_payload = {"prompt_text": "Write a one-sentence summary of A Midsummer Night's Dream."}
    run_test("Execute Prompt", "POST", f"{BASE_URL}/prompts/execute", execute_payload)

    optimize_payload = {
        "task_description": "Turn a statement into a question.",
        "examples": [{"input": "The sky is blue.", "output": "Is the sky blue?"}]
    }
    run_test("Optimize Prompt (APE)", "POST", f"{BASE_URL}/prompts/optimize", optimize_payload)

    benchmark_payload = {
        "prompt_text": "What are the three main benefits of using an API?",
        "models": ["gemini-2.5-flash-lite", "gpt-4.1-nano"]
    }
    run_test("Benchmark Prompt", "POST", f"{BASE_URL}/prompts/benchmark", benchmark_payload)
    
    diagnose_payload = {"prompt_text": "give me a story"}
    run_test("Diagnose Prompt", "POST", f"{BASE_URL}/prompts/diagnose", diagnose_payload)
    
    breakdown_payload = {
        "prompt_text": "You are a pirate chatbot. Rephrase the user's question in pirate speak. Do not answer it. Your response must be one sentence and include the word 'Ahoy!'. Example: if the user says 'Where is the treasure?', you say 'Ahoy, where be the treasure, matey?'"
    }
    run_test("Breakdown Prompt", "POST", f"{BASE_URL}/prompts/breakdown", breakdown_payload)

    # --- Test 15-19: Template Library and Composer Endpoints ---
    template_payload = {
      "name": "Test: Academic Summarizer",
      "description": "A template for creating concise, academic summaries.",
      "content": "You are an expert researcher. Summarize the key findings of the following text in three clear, academic bullet points. Text: {text_to_summarize}",
      "tags": ["summarize", "academic", "bullet_points"]
    }
    run_test("Create Template", "POST", f"{BASE_URL}/templates/", template_payload)

    run_test("List All Templates", "GET", f"{BASE_URL}/templates/")
    
    run_test("Filter Templates by Tag", "GET", f"{BASE_URL}/templates/?tag=academic")

    # This is the new test for the AI Template Generator
    generate_payload = {
        "style_description": "A persona template for a witty, sarcastic British butler.",
        "tags": ["persona", "sarcastic", "butler"]
    }
    run_test("AI Generate Template", "POST", f"{BASE_URL}/templates/generate", generate_payload)

    compose_payload = {
      "persona": "butler",
      "task": "summarize"
    }
    run_test("Compose Prompt", "POST", f"{BASE_URL}/templates/compose", compose_payload)

    # --- Test 20: Sandbox Endpoint ---
    sandbox_payload = {
      "prompts": [
        {
          "id": "v1_simple",
          "text": "Explain black holes."
        },
        {
          "id": "v2_detailed",
          "text": "You are an astrophysicist. Explain a black hole to a high school student in three paragraphs."
        }
      ],
      "input_text": "",
      "model": "gemini-2.5-flash-lite"
    }
    run_test("A/B Test Sandbox", "POST", f"{BASE_URL}/sandbox/", sandbox_payload)
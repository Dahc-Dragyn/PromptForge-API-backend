import requests
import json
import sys

# --- Configuration ---
BASE_URL = "http://127.0.0.1:8000"
HEADERS = {"Content-Type": "application/json", "accept": "application/json"}
DIAGNOSE_ENDPOINT = f"{BASE_URL}/prompts/diagnose"

def test_prompt_diagnosis(prompt_text: str, test_name: str):
    """
    Tests the /prompts/diagnose endpoint and verifies the response structure.
    """
    print(f"--- {test_name} ---")
    print(f"Testing prompt: '{prompt_text}'")
    payload = {"prompt_text": prompt_text}

    try:
        # 1. Make the API Call
        response = requests.post(DIAGNOSE_ENDPOINT, headers=HEADERS, data=json.dumps(payload))
        print(f"Status Code: {response.status_code}")
        response.raise_for_status()  # Exit on bad status (4xx or 5xx)

        response_json = response.json()
        print("Response JSON:")
        print(json.dumps(response_json, indent=2))

        # 2. Verify the Response Structure
        print("\n--- Verifying Response Structure ---")

        # Check for overall_score (must be a number)
        assert "overall_score" in response_json, "FAIL: 'overall_score' key is missing."
        assert isinstance(response_json["overall_score"], (int, float)), "FAIL: 'overall_score' is not a number."
        print("  ✅ 'overall_score' is present and is a number.")

        # Check for the criteria object
        assert "criteria" in response_json, "FAIL: 'criteria' key is missing."
        criteria = response_json["criteria"]
        print("  ✅ 'criteria' object is present.")

        # Check that all criteria fields are booleans
        expected_criteria_keys = ["clarity", "specificity", "context", "constraints"]
        for key in expected_criteria_keys:
            assert key in criteria, f"FAIL: '{key}' is missing from criteria."
            assert isinstance(criteria[key], bool), f"FAIL: criteria.{key} is not a boolean."
            print(f"  ✅ criteria.{key} is a boolean.")

        print(f"\n--- ✅ {test_name} PASSED ---")

    except requests.exceptions.RequestException as e:
        print(f"!!! TEST FAILED: Request Error - {e} !!!")
        if 'response' in locals() and response.text:
            print(f"Error Body: {response.text}")
        sys.exit(1)  # Exit with failure code
    except AssertionError as e:
        print(f"!!! TEST FAILED: Assertion Error - {e} !!!")
        sys.exit(1)  # Exit with failure code
    finally:
        print("-" * 40 + "\n")


if __name__ == "__main__":
    print("🚀 Starting focused test for the Prompt Ranking System...")

    # Test Case 1: A deliberately weak prompt to check the rubric
    test_prompt_diagnosis(
        prompt_text="write code",
        test_name="Test Case 1: Weak Prompt"
    )

    # Test Case 2: A much stronger prompt that should score higher
    strong_prompt = (
        "You are a senior Python developer. Write a function that takes a list of integers "
        "and returns a new list containing only the even numbers. Your response must be "
        "a single Python code block and nothing else. For example, given [1, 2, 3, 4], "
        "return [2, 4]."
    )
    test_prompt_diagnosis(
        prompt_text=strong_prompt,
        test_name="Test Case 2: Strong Prompt"
    )

    print("🎉 All ranking system tests completed successfully.")
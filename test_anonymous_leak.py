import requests
import json
import sys

# --- Configuration ---
BASE_URL = "http://127.0.0.1:8000/api/v1"
PROMPTS_ENDPOINT = f"{BASE_URL}/prompts/"

def print_header(title):
    """Prints a formatted header."""
    print("\n" + "="*15 + f" {title.upper()} " + "="*15)

def print_info(message):
    """Prints an informational message."""
    print(f"[*] {message}")

def print_result(success, message):
    """Prints a success or failure message."""
    if success:
        print(f"✅ PASS: {message}")
    else:
        print(f"❌ FAIL: {message}")

def run_anonymous_leak_test():
    """
    Tests the primary data leak hypothesis by making an unauthenticated
    request to the main data-fetching endpoint.
    """
    print_header("Anonymous Data Leak Test")
    print_info(f"Sending GET request to: {PROMPTS_ENDPOINT}")
    print_info("No 'Authorization' header is being sent with this request.")

    try:
        # Intentionally make the request with no auth headers
        response = requests.get(PROMPTS_ENDPOINT)
        status_code = response.status_code

        print_info(f"Response received with HTTP Status Code: {status_code}")

        # --- Analysis ---
        if status_code in [401, 403]:
            print_result(True, "The API correctly returned a permission error (401/403).")
            print_info("CONCLUSION: The backend is secure against anonymous requests. The bug is likely on the frontend.")
            return True

        elif status_code == 200:
            print_result(False, "The API returned a 200 OK status, indicating a critical security flaw.")
            try:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    print_info(f"The endpoint returned a list containing {len(data)} item(s).")
                    print_info("Sample of leaked data: " + json.dumps(data[0], indent=2))
                else:
                    print_info("The endpoint returned an empty list or non-list data.")

                print_info("\nCONCLUSION: HYPOTHESIS CONFIRMED. The backend is leaking data to unauthenticated users.")

            except json.JSONDecodeError:
                print_result(False, "The API returned 200 OK but the response was not valid JSON.")
            return False
        
        else:
            print_result(False, f"The API returned an unexpected status code: {status_code}.")
            print_info(f"Response body: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print_result(False, f"The test failed due to a connection error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    success = run_anonymous_leak_test()
    print("\nTest complete.")
    if not success:
        sys.exit(1)
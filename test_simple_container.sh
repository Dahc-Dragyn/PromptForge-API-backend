#!/bin/bash
# A new, simplified test script, built step-by-step.

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
# Set the base URL for the API
BASE_URL=${PROMPTFORGE_API_URL:-"http://localhost:8000"}

# IMPORTANT: This is the new token you just provided.
FIREBASE_ID_TOKEN="eyJhbGciOiJSUzI1NiIsImtpZCI6IjUwMDZlMjc5MTVhMTcwYWIyNmIxZWUzYjgxZDExNjUלאMmYxMjRmMjAiLCJ0eXAiOiJKV1QifQ.eyJuYW1lIjoiQ2hhZCBOeWdhcmQiLCJwaWN0dXJlIjoiaHR0cHM6Ly9saDMuZ29vZ2xldXNlcmNvbnRlbnQuY29tL2EvQUNnOG9jS0l6WktLcjRCamx2TGRTVHpoYzN6Yk9EY0lLU214YjkxOWtoTmFrVngweHlKU1czVDE9czk2LWMiLCJyb2xlIjoiYWRtaW4iLCJpc3MiOiJodHRwczovL3NlY3VyZXRva2VuLmdvb2dsZS5jb20vcHJvbXB0Zm9yZ2UtYzI3ZTgiLCJhdWQiOiJwcm9tcHRmb3JnZS1jMjdlOCIsImF1dGhfdGltZSI6MTc1ODU2Mzg0OSwidXNlcl9pZCI6Imd1SVBZYVNkdjFUTXZaOW5TQTQzdDQ3U3N0aTIiLCJzdWIiOiJndUlQWWFTZHYxVE12WjluU0E0M3Q0N1NzdGkyIiwiaWF0IjoxNzU4NTY0NTg2LCJleHAiOjE3NTg1NjgxODYsImVtYWlsIjoiQ2hhZC5ueWdhcmQxQGdtYWlsLmNNvbSIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJmaXJlYmFzZSI6eyJpZGVudGl0aWVzIjp7Imdvb2dsZS5jb20iOlsiMTA1MDQ2NTE3MTA1NDE2NTk4OTE5Il0sImVtYWlsIjpbImNoYWQubnlnYXJkMUBnbWFpbC5jb20iXX0sInNpZ25faW5fcHJvdmlkZXIiOiJnb29nbGUuY29tIn19.VxlRF-fu_bIXxtpgAprAtokN0SWr5sVQLnBIToxybyPmb6OHzAhFicLFIl1KMXiX8Jz79kYswKvM-N2qr9tWebHp15r7ZLw0aey8P40vvakogDbE5AmCJxoKI7Y1ho_6WAbrMJdm-W0B1QZq6KynrnjSTxAAn-NtRtER79Nl8hdzCfJiOy9YsWW7aqQGdFASM25qPk6P3S-yiW4eV4xVXRilmz9ngemIu5oavzo9l65o4E8Vyj9LZRjaiedz2uXXzH0QEFK9fT6uCYqnr14Oa5csDakfs5BpOF_ea9tSSo6tklAbhi-qW15-SBazkVModklmhwA3L5LPdV-gKrCq-w"
AUTH_HEADER="Authorization: Bearer $FIREBASE_ID_TOKEN"
USER_ID="guIPYaSdv1TMvZ9nSA43t47Ssti2"

# Check for required tools
if ! command -v jq &> /dev/null; then
    echo "❌ ERROR: jq is not installed. Please install it to run this script." >&2
    exit 1
fi

# --- Helper Function ---
run_test() {
    local test_name="$1"
    local expected_status="$2"
    local curl_args=("${@:3}")

    echo "--- Testing: $test_name ---" >&2

    response_body_file=$(mktemp)
    http_status=$(curl --silent --output "$response_body_file" --write-out "%{http_code}" "${curl_args[@]}")
    body=$(cat "$response_body_file")
    rm "$response_body_file"

    if [ "$http_status" -eq "$expected_status" ]; then
        echo "  ✅ SUCCESS: Received expected status code $http_status" >&2
        echo "$body"
    else
        echo "  ❌ FAILED: Expected status $expected_status, but got $http_status" >&2
        echo "  --- Response Body ---" >&2
        echo "$body" >&2
        echo "  ---------------------" >&2
        exit 1
    fi
}

echo "=================================================" >&2
echo "     Starting New Simplified API Test" >&2
echo "=================================================" >&2
echo "Targeting API at: $BASE_URL" >&2
echo "" >&2

# --- Step 1: Health Check ---
run_test "Health Check (GET /)" 200 curl -X GET "$BASE_URL/"

echo "" >&2
echo "✅ Health check passed. Base script is working." >&2
echo "=================================================" >&2


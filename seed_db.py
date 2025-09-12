import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"
HEADERS = {"Content-Type": "application/json", "accept": "application/json"}

# A list of high-value templates we want our AI to generate
TEMPLATES_TO_GENERATE = [
    {
        "style_description": "A persona for a Socratic Teacher who answers questions with more insightful questions to guide the user to the answer themselves.",
        "tags": ["persona", "education", "socratic_method"]
    },
    {
        "style_description": "A style for a Playful Explainer that breaks down complex scientific topics using simple analogies and a touch of humor.",
        "tags": ["style", "explainer", "playful", "science"]
    },
    {
        "style_description": "A format for a Formal Business Proposal, including sections for Executive Summary, Problem Statement, Proposed Solution, and Pricing.",
        "tags": ["format", "business", "proposal", "formal"]
    },
    {
        "style_description": "A persona for a Startup Growth Hacker brainstorming a list of unconventional marketing ideas.",
        "tags": ["persona", "marketing", "startup", "brainstorming"]
    },
    {
        "style_description": "A style for a Persuasive Ad Copywriter focused on creating short, punchy, and emotionally resonant text for social media ads.",
        "tags": ["style", "marketing", "ad_copy", "persuasive"]
    },
    {
        "style_description": "A format for a Structured Technical Documentation page, with clear sections for API endpoints, parameters, and example code.",
        "tags": ["format", "technical_writing", "documentation", "api"]
    },
    {
        "style_description": "A persona for an Empathetic Customer Support Agent who is patient, understanding, and provides clear, step-by-step solutions.",
        "tags": ["persona", "customer_support", "empathetic"]
    },
    {
        "style_description": "A style for a Humorous Social Media Post that is witty, slightly sarcastic, and optimized for engagement on platforms like X (formerly Twitter).",
        "tags": ["style", "social_media", "humorous", "sarcastic"]
    },
    {
        "style_description": "A format for a Detailed Recipe Card, including ingredients, step-by-step instructions, prep time, and cook time.",
        "tags": ["format", "recipe", "cooking"]
    },
    {
        "style_description": "A persona for a Skeptical Financial Analyst who critiques a business idea, focusing on potential risks, market saturation, and profitability.",
        "tags": ["persona", "finance", "analysis", "skeptical"]
    }
]

def generate_template(description, tags):
    """Calls the API to generate and store a single template."""
    payload = {
        "style_description": description,
        "tags": tags
    }
    url = f"{BASE_URL}/templates/generate"
    
    try:
        print(f"-> Generating template for: '{description[:50]}...'")
        response = requests.post(url, headers=HEADERS, data=json.dumps(payload), timeout=60)
        
        if response.status_code == 201:
            template_name = response.json().get("name", "Unknown Template")
            print(f"   ... Success! Created '{template_name}'")
            return True
        elif response.status_code == 409:
             print(f"   ... Skipped. Template with a similar name already exists.")
             return True # Not a failure, just already done
        else:
            print(f"   !!! FAILED with status {response.status_code} !!!")
            print(f"   Error: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"   !!! FAILED with exception: {e} !!!")
        return False

def main():
    print("🚀 Starting to seed the template library...\n")
    
    success_count = 0
    for template_spec in TEMPLATES_TO_GENERATE:
        if generate_template(template_spec["style_description"], template_spec["tags"]):
            success_count += 1
        time.sleep(1) # Add a small delay to avoid overwhelming the server

    print(f"\n✅ Seeding complete. Successfully generated {success_count}/{len(TEMPLATES_TO_GENERATE)} templates.")
    print("Check your Firestore database to see the new templates!")

if __name__ == "__main__":
    main()
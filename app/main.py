from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import prompts, templates, sandbox 

# Initialize the FastAPI app
app = FastAPI(
    title="PromptForge API",
    description="API for managing and optimizing LLM prompts.",
    version="0.1.0",
    root_path="/api/promptforge"
)

# --- THIS IS THE FIX ---
# Define the specific origins that are allowed to connect.
# Using a wildcard "*" is not allowed when allow_credentials=True.
origins = [
    # This is your frontend's deployed URL
    "https://3000-firebase-prompforge-ui-1756407924093.cluster-feoix4uosfhdqsuxofg5hrq6vy.cloudworkstations.dev",
    # This is for local development
    "http://localhost:3000",
]

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, # Use the specific list of origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Endpoints ---
app.include_router(prompts.router)
app.include_router(templates.router) 
app.include_router(sandbox.router)

@app.get("/", tags=["Health Check"])
def read_root():
    """Confirms the API is running."""
    return {"status": "ok", "message": "Welcome to the PromptForge API!"}
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# --- FIX 1: Import the new logging middleware ---
from app.middleware.logging_middleware import LoggingMiddleware
from app.routers import prompts, templates, sandbox, metrics, execution

# Initialize the FastAPI app
app = FastAPI(
    title="PromptForge API",
    description="API for managing and optimizing LLM prompts.",
    version="0.1.0",
)

# --- FIX 2: Add the new logging middleware to the application ---
# This should be one of the first middleware added to log as much as possible.
app.add_middleware(LoggingMiddleware)


# Define the specific origins that are allowed to connect.
origins = [
    # This is your frontend's deployed URL
    "https://3000-firebase-prompforge-ui-1756407924093.cluster-feoix4uosfhdqsuxofg5hrq6vy.cloudworkstations.dev",
    # This is for local development
    "http://localhost:3000",
    # Your Ngrok URL
    "https://db4f-24-22-90-227.ngrok-free.app",
]

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Endpoints ---
app.include_router(prompts.router)
app.include_router(templates.router)
app.include_router(sandbox.router)
app.include_router(metrics.router)
app.include_router(execution.router)

@app.get("/", tags=["Health Check"])
def read_root():
    """Confirms the API is running."""
    return {"status": "ok", "message": "Welcome to the PromptForge API!"}
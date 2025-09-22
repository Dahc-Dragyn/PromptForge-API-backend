from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from logging.handlers import RotatingFileHandler

# --- FIX 1: Configure a rotating file handler ---
# The logger from the middleware will inherit this configuration.
log_formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')

log_handler = RotatingFileHandler(
    'api_requests.log',
    mode='a',
    maxBytes=1024,  # 1KB for testing - a very small size to force rotation quickly
    backupCount=3,
    encoding=None,
    delay=0
)
log_handler.setFormatter(log_formatter)
log_handler.setLevel(logging.INFO)

# Get the root logger and add our handler to it.
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(log_handler)

# --- FIX 2: Import the original logging middleware ---
from app.middleware.logging_middleware import LoggingMiddleware
from app.routers import prompts, templates, sandbox, metrics, execution
from app.core.db import initialize_firebase  # Added back for Firebase setup

# Initialize Firebase
initialize_firebase()

# Initialize the FastAPI app
app = FastAPI(
    title="PromptForge API",
    description="API for managing and optimizing LLM prompts.",
    version="0.1.0",
)

# Add the logging middleware to the application
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
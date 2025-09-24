# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from logging.handlers import RotatingFileHandler
from app.middleware.logging_middleware import LoggingMiddleware
from app.routers import prompts, templates, sandbox, metrics, execution
from app.core.db import initialize_firebase

# --- Logging and Firebase setup remains the same ---
log_formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
log_handler = RotatingFileHandler('api_requests.log', mode='a', maxBytes=5*1024*1024, backupCount=3)
log_handler.setFormatter(log_formatter)
log_handler.setLevel(logging.INFO)
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(log_handler)
initialize_firebase()

# --- App Initialization ---
app = FastAPI(
    title="PromptForge API",
    description="API for managing and optimizing LLM prompts.",
    version="0.1.0",
)

app.add_middleware(LoggingMiddleware)

# --- CORS Configuration ---
origins = [
    "https://3000-firebase-prompforge-ui-1756407924093.cluster-feoix4uosfhdqsuxofg5hrq6vy.cloudworkstations.dev",
    "http://localhost:3000",
    "https://db4f-24-22-90-227.ngrok-free.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Endpoints ---
# FIX: Add the required '/api/promptforge' prefix to all routers.
app.include_router(prompts.router, prefix="/api/promptforge")
app.include_router(templates.router, prefix="/api/promptforge")
app.include_router(sandbox.router, prefix="/api/promptforge")
app.include_router(metrics.router, prefix="/api/promptforge")
app.include_router(execution.router, prefix="/api/promptforge")

@app.get("/", tags=["Health Check"])
def read_root():
    """Confirms the API is running."""
    return {"status": "ok", "message": "Welcome to the PromptForge API!"}
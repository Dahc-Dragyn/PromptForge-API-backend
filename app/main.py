# app/main.py
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
import logging
from logging.handlers import RotatingFileHandler
from app.middleware.logging_middleware import LoggingMiddleware
from app.routers import prompts, templates, sandbox, metrics, execution
from app.core.db import initialize_firebase

# --- Logging and Firebase setup ---
# This section remains unchanged.
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
    version="1.0.1",
)

# --- Middleware ---
app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Router Configuration ---
# A single router is used to prefix all routes with /api/v1.
api_router = APIRouter()

# Each of these lines registers a section of your API.
# The `metrics.router` line is essential and fixes the 404 errors.
api_router.include_router(prompts.router, prefix="/prompts")
api_router.include_router(templates.router, prefix="/templates")
api_router.include_router(sandbox.router, prefix="/sandbox")
api_router.include_router(metrics.router, prefix="/metrics")
api_router.include_router(execution.router, prefix="/users")

# Include the main router with the versioned prefix
app.include_router(api_router, prefix="/api/v1")


# --- Root Health Check ---
@app.get("/", tags=["Health Check"])
def read_root():
    """Confirms the API is running."""
    return {"status": "ok", "message": "Welcome to the PromptForge API v1!"}
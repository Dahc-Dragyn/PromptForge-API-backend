import os
import time
import json
import logging
import sys
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI, APIRouter, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# --- New Security Imports ---
from redis.asyncio import Redis
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# --- Internal Imports ---
from app.middleware.logging_middleware import LoggingMiddleware
from app.routers import prompts, templates, sandbox, metrics, execution
from app.core.db import initialize_firebase

# --------------------------------------------------------------------
# 1. Configuration & Setup
# --------------------------------------------------------------------

# Load environment variables
load_dotenv()
REDIS_URL = os.getenv("REDIS_URL", "redis://redis-service:6379")

# Setup Logging (Preserving your existing config)
log_formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
log_handler = RotatingFileHandler('api_requests.log', mode='a', maxBytes=5*1024*1024, backupCount=3)
log_handler.setFormatter(log_formatter)
log_handler.setLevel(logging.INFO)
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(log_handler)

initialize_firebase()

# --- SECURITY: Redis Connection ---
try:
    cache = Redis.from_url(REDIS_URL, decode_responses=True, encoding="utf-8")
    root_logger.info("Redis cache connection established for PromptForge.")
except Exception as e:
    root_logger.error(f"Could not initialize Redis. Security features disabled. Error: {e}")
    cache = None

# --- SECURITY: Proxy-Aware IP Detection ---
def get_real_ip(request: Request):
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host or "127.0.0.1"

# --- SECURITY: Initialize Rate Limiter ---
limiter = Limiter(key_func=get_real_ip, storage_uri=REDIS_URL, default_limits=["100/minute"])

# --------------------------------------------------------------------
# 2. App Initialization
# --------------------------------------------------------------------

app = FastAPI(
    title="PromptForge API",
    description="API for managing and optimizing LLM prompts.",
    version="1.0.1",
)

# Connect Limiter to App
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --------------------------------------------------------------------
# 3. Security Middleware (Must Run First)
# --------------------------------------------------------------------

# --- LAYER 1: The "Bouncer" (Bot Block) ---
@app.middleware("http")
async def block_bad_bots(request: Request, call_next):
    user_agent = request.headers.get("user-agent", "").lower()
    bad_bots = ["gptbot", "bytespider", "claudebot", "ccbot", "anthropic-ai", "omgilibot", "facebookexternalhit"]
    
    if any(bot in user_agent for bot in bad_bots):
        root_logger.warning(f"BLOCKED BOT: {user_agent} from {get_real_ip(request)}")
        return Response(
            content=json.dumps({"detail": "Bot access denied."}), 
            status_code=status.HTTP_403_FORBIDDEN,
            media_type="application/json"
        )
    return await call_next(request)

# --- LAYER 2: The "Velocity Trap" (Anti-Scraper) ---
@app.middleware("http")
async def velocity_trap(request: Request, call_next):
    if not cache: return await call_next(request)

    client_ip = get_real_ip(request)
    
    # Check Jail
    is_banned = await cache.get(f"ban:{client_ip}")
    if is_banned:
        return Response(
            content=json.dumps({"detail": "IP Banned for suspicious velocity. Try again in 1 hour."}), 
            status_code=status.HTTP_403_FORBIDDEN,
            media_type="application/json"
        )

    # Check Velocity (Requests per Second)
    current_time = int(time.time())
    velocity_key = f"vel:{client_ip}:{current_time}"
    
    try:
        request_count = await cache.incr(velocity_key)
        if request_count == 1:
            await cache.expire(velocity_key, 2)
            
        # Limit: 15 requests per second (Higher than Bookfinder because LLMs are bursty)
        if request_count > 15:
            root_logger.error(f"VELOCITY BAN: {client_ip} hit {request_count} req/s")
            await cache.setex(f"ban:{client_ip}", 3600, "banned")
            return Response(
                content=json.dumps({"detail": "Velocity limit exceeded. You are banned."}),
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                media_type="application/json"
            )
    except Exception:
        pass # Fail open if Redis hiccups

    return await call_next(request)

# --------------------------------------------------------------------
# 4. Standard Middleware & Routers
# --------------------------------------------------------------------

app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_router = APIRouter()
api_router.include_router(prompts.router, prefix="/prompts")
api_router.include_router(templates.router, prefix="/templates")
api_router.include_router(sandbox.router, prefix="/sandbox")
api_router.include_router(metrics.router, prefix="/metrics")
api_router.include_router(execution.router, prefix="/users")

app.include_router(api_router, prefix="/api/v1")

@app.get("/", tags=["Health Check"])
def read_root():
    """Confirms the API is running."""
    return {"status": "ok", "message": "Welcome to the PromptForge API v1!"}
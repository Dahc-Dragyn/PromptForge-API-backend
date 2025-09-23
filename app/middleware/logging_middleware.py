# app/middleware/logging_middleware.py
import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
import logging

# FIX 1: Remove the redundant logging.basicConfig. Configuration is now in main.py.
# FIX 2: Get a logger instance. It will inherit the root configuration.
logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Intercepts all requests to log key information to the configured log file.
        """
        start_time = time.time()

        response = await call_next(request)

        process_time_ms = (time.time() - start_time) * 1000

        user_id = "anonymous"
        if hasattr(request.state, "user") and request.state.user:
            user_id = request.state.user.get("uid", "unknown")
        
        log_message = (
            f"method={request.method} "
            f"path='{request.url.path}' "
            f"status_code={response.status_code} "
            f"user_id='{user_id}' "
            f"client_ip='{request.client.host}' "
            f"latency_ms={process_time_ms:.2f}"
        )
        
        logger.info(log_message)
        
        return response
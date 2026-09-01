import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)

logger = logging.getLogger(__name__)


class RequestMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        start = time.perf_counter()

        response: Response = await call_next(request)

        elapsed = time.perf_counter() - start
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{elapsed:.4f}"

        logger.info(
            "%s %s - %s - %.4fs",
            request.method,
            request.url.path,
            response.status_code,
            elapsed,
        )
        return response
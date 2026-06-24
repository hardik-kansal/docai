from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from .auth.routes import router
from contextlib import asynccontextmanager
from .config import settings
import redis.asyncio as redis  # if just do import redis-> sync lib, fails at runtime
from .auth.dependencies import (
    set_redis_pool,
    get_redis_pool,
    set_asyncpg_pool,
    get_asyncpg_pool,
)
import asyncpg
import logging
import time
import uuid
import json

logging.basicConfig(level=logging.INFO if settings().is_prod else logging.DEBUG)
logger = logging.getLogger(__name__)


# wraps all http req
# browser-> middleware -> dispatch() -> call_next()  calls route, returns response
# correlation id header added to response -> middleware return response send to client
class RouteMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        correlation_id = getattr(request.state, "correlation_id", None)
        if correlation_id is None:
            correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        # in larger systems there may already be a correlation ID generated upstream
        # say be cloudfare

        request.state.correlation_id = correlation_id

        try:
            response: Response = await call_next(request)

            # calls route endpoint or next middleware
        except Exception as exc:
            process_time = (time.perf_counter() - start_time) * 1000  # returns in s
            self._log_request(
                request, 500, process_time, correlation_id, error=str(exc)
            )
            raise

        process_time = (time.perf_counter() - start_time) * 1000
        self._log_request(request, response.status_code, process_time, correlation_id)
        return response  # python does not have block scope like c++ for try/except
        # only if try actually runs.

    def _log_request(
        self,
        request: Request,
        status_code: int,
        duration_ms: float,
        correlation_id: str,
        error: str = None,
    ):
        log_payload = {
            "correlation_id": correlation_id,
            "http_method": request.method,
            "path": request.url.path,
            "status_code": status_code,  # for errors ->500
            "duration_ms": round(duration_ms, 2),
            "client_ip": request.client.host if request.client else "unknown",
        }

        if error:
            log_payload["error"] = error
            logger.error(json.dumps(log_payload))  # to string of jsons
        else:
            logger.info(json.dumps(log_payload))


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("connecting to redis", extra={"REDIS_URL": settings().REDIS_URL})
    start_time = time.perf_counter()
    _redis_pool = redis.Redis.from_url(
        settings().REDIS_URL,  # e.g. "redis://localhost:6379/0"
        decode_responses=True,
        # redis.set("name","hardik")
        # redis.get("name")-> returns b"hardik"
        # setting this to true causes it to return "hardik"
        max_connections=20,  # async 20 requests to reddis, after 20 wait and reuse
    )
    try:
        await _redis_pool.ping()
    except Exception:
        logger.critical("failed to connect to redis on startup", exc_info=True)
        raise

    logger.info(
        "redis connected",
        extra={"elapsed_ms": round((time.perf_counter() - start_time) * 1000, 2)},
    )
    # before startup
    set_redis_pool(_redis_pool)
    start_time = time.perf_counter()
    logger.info("connecting to db", extra={"DB_URL": settings().DB_URL})
    try:
        _pool = await asyncpg.create_pool(
            settings().DB_URL,
            min_size=5,
            # first 5 connections immediately
            # even if nobody using them
            # to make sure first 5 doesnt need to wait for connection
            max_size=10,
            statement_cache_size=1024,  # defaut though
            # postgres parse+plan+execute
            # for first 1024 unique queries for each connection
            # caches planning and execute faster
            # This means exactly repeated queries skip the Postgres parse+plan phase.
            # pgbouncer ???
        )
    except Exception:
        logger.critical("failed to connect to db on startup", exc_info=True)
        raise
    logger.info(
        "db connected",
        extra={"elapsed_ms": round((time.perf_counter() - start_time) * 1000, 2)},
    )
    set_asyncpg_pool(_pool)
    yield
    logger.info("shutting down: closing redis pool")
    try:
        await get_redis_pool().aclose()
        logger.info("redis disconnected")
    except Exception:
        logger.error("error while closing redis pool", exc_info=True)
        raise
    finally:  # very imp
        # since without it, if redis close failed, then db connection wont be close
        logger.info("shutting down: closing db pool")
        try:
            await get_asyncpg_pool().close()
        except Exception:
            logger.error("error while closing db pool", exc_info=True)
            raise
        logger.info("db disconnected")


app = FastAPI(lifespan=lifespan)
app.include_router(router)
app.add_middleware(RouteMiddleware)

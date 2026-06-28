from backend.auth.tokens import TokenPayload
from fastapi import FastAPI, Depends
from typing import Annotated
from .auth.routes import router
from contextlib import asynccontextmanager
from .config import settings
from .logging_config import RouteMiddleware
import redis.asyncio as redis  # if just do import redis-> sync lib, fails at runtime
from .auth.dependencies import (
    set_redis_pool,
    get_redis_pool,
    set_asyncpg_pool,
    get_asyncpg_pool,
    get_current_user,
)
import asyncpg
import logging
import time


logging.basicConfig(level=logging.INFO if settings().is_prod else logging.DEBUG)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("connecting to redis")
    start_time = time.perf_counter()
    _redis_pool = redis.Redis.from_url(
        settings().REDIS_URL,  # e.g. "redis://localhost:6379/0"
        decode_responses=True,
        # redis.set("name","hardik")
        # redis.get("name")-> returns b"hardik"
        # setting this to true causes it to return "hardik"
        max_connections=20,  # async 20 requests to reddis, after 20 wait and reuse
    )  # connection object is created here
    try:
        await _redis_pool.ping()
    except Exception:
        logger.critical("failed to connect to redis on startup")
        await _redis_pool.aclose()
        raise

    logger.info(
        "redis connected",
        extra={"elapsed_ms": round((time.perf_counter() - start_time) * 1000, 2)},
    )
    set_redis_pool(_redis_pool)

    start_time = time.perf_counter()
    logger.info("connecting to db")
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
        )  # this is atomic, either succeeds or no assignment at all
        # no need to close connection in this case
    except Exception:
        logger.critical("failed to connect to db on startup")
        raise

    logger.info(
        "db connected",
        extra={"elapsed_ms": round((time.perf_counter() - start_time) * 1000, 2)},
        # gets saved as record.attr
    )
    set_asyncpg_pool(_pool)

    # before startup
    yield
    # after startup

    logger.info("closing redis pool")
    try:
        await get_redis_pool().aclose()
        logger.info("redis disconnected")
    except Exception:
        logger.error("error while closing redis pool")
        raise
    finally:  # very imp
        # since without it, if redis close failed, then db connection wont be close
        logger.info("shutting down: closing db pool")
        try:
            await get_asyncpg_pool().close()
            logger.info("db disconnected")
        except Exception:
            logger.error("error while closing db pool")
            raise


app = FastAPI(lifespan=lifespan)
app.include_router(router)
app.add_middleware(RouteMiddleware)


@app.get("/")
async def home(user: Annotated[TokenPayload, Depends(get_current_user)]):
    return user

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
    User,
)
from .ingestion.dependencies import set_boto3_client, get_boto3_client
import asyncpg
import logging
import time
import boto3
from botocore.config import Config
import contextlib

logger = logging.getLogger(__name__)


async def redis_start():
    logger.info("connecting to redis")
    start_time = time.perf_counter()
    _redis_pool = redis.Redis.from_url(
        settings().REDIS_URL,
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


async def pg_start():
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


def s3_start() -> boto3.client:
    start_time = time.perf_counter()
    logger.info("connecting to s3")
    client: boto3.client = boto3.client(
        "s3",
        endpoint_url=settings().minio_endpoint,
        aws_access_key_id=settings().minio_access_key,
        aws_secret_access_key=settings().minio_secret_key,
        region_name=settings().minio_region,
        config=Config(
            max_pool_connections=50,
            retries={"max_attempts": 3, "mode": "adaptive"},
            connect_timeout=5,
            read_timeout=30,
        ),
    )
    try:
        client.list_buckets()  # boto3 is sync lib never use inside tradional routes
    except Exception:
        logger.critical("failed to connect to s3 on startup")
        raise

    logger.info(
        "s3 connected",
        extra={"elapsed_ms": round((time.perf_counter() - start_time) * 1000, 2)},
    )
    set_boto3_client(client)


# runs all functions even if any crashed
# ELSE req nested way, close redis, use finally close pg, use finally, so on
async def shutdown_all_services():
    logger.info("Initiating global service shutdown sequence...")
    async with contextlib.AsyncExitStack() as stack:
        #  will execute in REVERSE order (Last in, First out).
        stack.push_async_callback(get_asyncpg_pool().close)
        stack.push_async_callback(get_redis_pool().aclose)
        stack.push_async_callback(get_boto3_client().close)
        # if passed as .close() executes immediately


@asynccontextmanager
async def lifespan(app: FastAPI):
    await redis_start()
    await pg_start()
    s3_start()

    # before startup
    yield
    # after startup
    try:
        await shutdown_all_services()
    except Exception:
        logger.critical("shutdown failed")
        raise


app = FastAPI(lifespan=lifespan)
app.include_router(router)
app.add_middleware(RouteMiddleware)


@app.get("/")
async def home(user: Annotated[User, Depends(get_current_user)]):
    return user

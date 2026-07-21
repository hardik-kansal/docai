import asyncio
from fastapi.responses import JSONResponse
from qdrant_client import AsyncQdrantClient, models
from fastembed import TextEmbedding
from fastembed.rerank.cross_encoder import TextCrossEncoder
from fastapi import FastAPI, Depends, Request
from typing import Annotated
from .auth.routes import router as auth_router
from .ingestion.routes import router as s3_router
from .query.routes import router as query_router
from contextlib import asynccontextmanager
from .config import settings
from .logging_config import RouteMiddleware
from .query.dependencies import GroundedJsonException
from google import genai
import redis.asyncio as redis  # if just do import redis-> sync lib, fails at runtime
from .auth.dependencies import (
    set_redis_pool,
    get_redis_pool,
    set_asyncpg_pool,
    get_asyncpg_pool,
    get_current_user,
    User,
)
from .ingestion.dependencies import (
    set_boto3_client,
    get_boto3_client,
    set_embedModel,
    set_vectorPool,
    get_vectorPool,
)
from .query.dependencies import set_reranker, set_llm
import asyncpg
import logging
import time
import boto3
from botocore.config import Config
import contextlib
import logfire
import json
from .dependencies import get_connections_event

logfire.configure(token=settings().LOGFIRE_TOKEN)
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
        endpoint_url=settings().MINIO_URL,
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


def embed_model():
    embedModel = TextEmbedding(model_name=settings().EMBED_MODEL_ID)
    set_embedModel(embedModel)


def reranker_start():
    reranker = TextCrossEncoder(model_name=settings().RERANK_MODEL_ID)
    set_reranker(reranker)


def llm_start():
    client = genai.Client(api_key=settings().GEMINI_KEY)
    set_llm(client)


async def vector_db_start():
    vectorPool = AsyncQdrantClient(
        url=settings().QDRANT_URL,
        api_key=settings().QDRANT_API_KEY,
    )
    name = settings().COLLECTION
    if not await vectorPool.collection_exists(name):
        await vectorPool.create_collection(
            collection_name=name,
            vectors_config={
                "dense": models.VectorParams(
                    size=settings().EMBED_MODEL_DIM, distance=models.Distance.COSINE
                )
            },
            sparse_vectors_config={
                "sparse": models.SparseVectorParams(modifier=models.Modifier.IDF)
            },
        )
        for field, schema in [
            ("user_id", models.PayloadSchemaType.KEYWORD),
            ("document_id", models.PayloadSchemaType.KEYWORD),
        ]:
            await vectorPool.create_payload_index(
                name, field_name=field, field_schema=schema
            )
    set_vectorPool(vectorPool)


# runs all functions even if any crashed
# ELSE req nested way, close redis, use finally close pg, use finally, so on
async def shutdown_all_services():
    logger.info("Initiating global service shutdown sequence...")
    async with contextlib.AsyncExitStack() as stack:
        #  will execute in REVERSE order (Last in, First out).
        stack.push_async_callback(get_asyncpg_pool().close)
        stack.push_async_callback(get_redis_pool().aclose)
        stack.push_async_callback(get_vectorPool().close)
        stack.callback(get_boto3_client().close)  # boto3 is sync
        # if passed as .close() executes immediately


async def redis_listener() -> None:
    # though celery creates a new client per worker
    # and assign it to same redis client, it is auth one
    # since celery take a snapshot of code (not of runtime)
    pubsub = get_redis_pool().pubsub()
    await pubsub.subscribe(settings().REDIS_CHANNEL_DOCS)  # coroutine
    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            """
            this is first msg which is received, which just confirms 
            subscription and actual data is in type message inside "data"
            {
                "type": "subscribe",
                "pattern": None,
                "channel": "events",
                "data": 1
            }
            """
            try:
                # use .get if we want to loop over it
                payload = json.loads(message["data"])
                user_id = payload["user_id"]
            except (KeyError, json.JSONDecodeError):
                logger.warning("bad payload")
                continue

            # use .get(), never connections[user_id]
            # the latter would make a defaultdict silently
            # means create an empty set for every user_id
            # even if that user not actually listening
            # waste space, as connections store large no of empty sets
            for q in list(get_connections_event().get(user_id, ())):
                # this user_id set could be deleted in between
                # which can cause RuntimeError:Set changed size during iteration
                # does why did list to create a copy instead

                if q.full():
                    try:  # suppose execution to user_id sse part,
                        # this q might emptied
                        q.get_nowait()  # drop oldest
                    except asyncio.QueueEmpty:
                        pass
                q.put_nowait(payload)
                # put to queue which might have also discarded from connections
                # by client sse function
                # means could not discover through connections
                # but still exist, but with no ref so after this completes
                # eventually gonna clear out
    except asyncio.CancelledError:
        pass  # though lifespan already handles it
    finally:
        await pubsub.unsubscribe(settings().REDIS_CHANNEL_DOCS)
        await pubsub.aclose()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await redis_start()
    await pg_start()
    await vector_db_start()
    s3_start()
    embed_model()
    reranker_start()
    llm_start()
    task = asyncio.create_task(redis_listener())
    logger.info("redis_listener started")

    # before startup
    yield
    # before shutdown

    try:
        task.cancel()  # only registers it as canceled
        await task
        # waiting we actually get out of task which happens
        # when control give back to event loop in next await or asycn for
    except asyncio.CancelledError:
        pass
    try:
        await shutdown_all_services()
    except Exception:
        logger.critical("shutdown failed")
        raise


app = FastAPI(lifespan=lifespan, docs_url=None)
app.include_router(auth_router)
app.include_router(s3_router)
app.include_router(query_router)
app.add_middleware(RouteMiddleware)
logfire.instrument_fastapi(app)
logfire.instrument_httpx()
logfire.instrument_asyncpg()
logfire.instrument_celery()
logfire.instrument_redis()


@app.exception_handler(GroundedJsonException)
async def guardrail_exception_handler(request: Request, exc: GroundedJsonException):
    return JSONResponse(
        status_code=exc.status_code, content=exc.grounded_answer.model_dump()
    )


@app.get("/")
async def home(user: Annotated[User, Depends(get_current_user)]):
    return user


@app.get("/docs")
async def docs_redirect():
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="https://github.com/hardik-kansal/docai#readme")

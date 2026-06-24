from fastapi import FastAPI
from .auth.routes import router
from contextlib import asynccontextmanager
from .config import settings
import redis.asyncio as redis  # if just do import redis-> sync lib, fails at runtime
from .auth.dependencies import set_redis_pool, get_redis_pool
import asyncpg
from .db.dependencies import set_asyncpg_pool, get_asyncpg_pool
import logging

logging.basicConfig(level=logging.INFO if settings().is_prod else logging.DEBUG)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # dependencies or inside it tokenstore redispool stays none
    _redis_pool = redis.Redis.from_url(
        settings().REDIS_URL,  # e.g. "redis://localhost:6379/0"
        decode_responses=True,
        # redis.set("name","hardik")
        # redis.get("name")-> returns b"hardik"
        # setting this to true causes it to return "hardik"
        max_connections=20,  # async 20 requests to reddis, after 20 wait and reuse
    )
    logger.info("redis connected")
    # before startup
    set_redis_pool(_redis_pool)
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
    logger.info("postgresql connected")
    set_asyncpg_pool(_pool)
    yield
    await get_redis_pool().aclose()
    logger.info("redis disconnected")
    await get_asyncpg_pool().close()
    logger.info("postgresql disconnected")


app = FastAPI(lifespan=lifespan)
app.include_router(router)

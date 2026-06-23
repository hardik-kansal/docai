from fastapi import FastAPI
from .auth.routes import router
from contextlib import asynccontextmanager
from .config import settings
import redis.asyncio as redis  # if just do import redis-> sync lib, fails at runtime
from .auth.dependencies import set_redis_pool, get_redis_pool


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
    # before startup
    set_redis_pool(_redis_pool)
    yield
    # after startup
    await get_redis_pool().aclose()


app = FastAPI(lifespan=lifespan)
app.include_router(router)

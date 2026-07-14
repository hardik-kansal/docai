from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    # pydantic looks for .env
    # if .env has extra vars then extra="ignore" ignores them
    # model_config must not be renamed, else looks for os env directly
    JWT_SECRET: str  # required
    JWT_ALGORITHM: str
    ISSUER: str
    REDIS_URL: str
    DB_URL: str
    is_prod: bool  # "false converts to 0"

    # MinIO / S3
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str
    minio_region: str
    MINIO_NOTIFY_WEBHOOK_AUTH_TOKEN_FASTAPI: str

    # Ingestion limits
    max_file_size_bytes: int
    presigned_url_expiry_seconds: int
    stream_chunk_size_bytes: int

    EMBED_MODEL_ID: str
    MAX_TOKENS: int
    EMBED_MODEL_DIM: int
    RERANK_MODEL_ID: str

    QDRANT_URL: str
    QDRANT_API_KEY: str
    COLLECTION: str

    GEMINI_KEY: str
    GEMINI_MODEL: str

    system_prompt: str

    LOGFIRE_TOKEN: str

    REDIS_CHANNEL_DOCS: str
    PING_INTERVAL: int = 15  # seconds — must be < any proxy idle timeout
    QUEUE_MAXSIZE: int = 5
    # user can open multiple tabs/mobile say, and then upload document
    # each doc uploaded create a redis event
    # all tabs have thieir own sse session to look for status update
    # now if user do it for say 6 tabs, 6 events will be send to each queue
    # but queue size is 5, say if queue event is not processed(send via sse)
    # before 6th event came, oldest event would be discard by redis_listener
    # so client endpoint would not recieve oldest event.
    # but it is already stored in database, so refreshing would work fine.


@lru_cache(maxsize=1)
def settings() -> Settings:
    return Settings()


# can be used with Depends(callable settings now) insde tree of func called by fastapi
# env read only once, then returns same object cached, like if do settings=Settings()
# helps in testing by mocking it, i.e .env is not read

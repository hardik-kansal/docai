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

    # Ingestion limits
    max_file_size_bytes: int
    presigned_url_expiry_seconds: int
    stream_chunk_size_bytes: int


@lru_cache(maxsize=1)
def settings() -> Settings:
    return Settings()


# can be used with Depends(callable settings now) insde tree of func called by fastapi
# env read only once, then returns same object cached, like if do settings=Settings()
# helps in testing by mocking it, i.e .env is not read

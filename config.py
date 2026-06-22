from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")  # pydantic looks for .env
    # model_config must not be renamed, else looks for os env directly
    JWT_SECRET: str  # required
    JWT_ALGORITHM: str
    TOKEN_EXPIRY_MINUTES: int = 60  # not required, have default value
    ISSUER: str


@lru_cache(maxsize=1)
def settings():
    return Settings()


# can be used with Depends(callable settings now)
# env read only once, then returns same object cached, like if do settings=Settings()
# helps in testing by mocking it, i.e .env is not read

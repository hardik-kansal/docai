from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="/.env")  # pydantic looks for .env
    # model_config must not be renamed, else looks for os env directly
    _JWT_SECRET: str  # required
    _JWT_ALGORITHM: str
    _TOKEN_EXPIRY_MINUTES: int = 60
    _ISSUER: str


settings = Settings()

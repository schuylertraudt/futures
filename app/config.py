from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    odds_api_key: str = ""
    kalshi_email: str = ""
    kalshi_password: str = ""
    cache_dir: str = "cache"
    cache_ttl_seconds: int = 7200
    kalshi_cache_ttl_seconds: int = 1800
    books: list[str] = Field(
        default=[
            "draftkings",
            "fanduel",
            "betmgm",
            "caesars",
            "betrivers",
            "fanatics",
            "thescore_bet",
            "pinnacle",
        ]
    )
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {"env_file": ".env"}


settings = Settings()

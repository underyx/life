from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    secret_key: str
    data_dir: str = "/data"
    base_url: str = "https://life.ts.bence.dev"

    model_config = {"env_prefix": "LIFE_"}


settings = Settings()

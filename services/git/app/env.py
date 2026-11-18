from pydantic_settings import BaseSettings, SettingsConfigDict


class Env(BaseSettings):
    SECRET: str
    POSTGRES_DSN: str

    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_")


env = Env()

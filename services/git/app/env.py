import pathlib

from pydantic import DirectoryPath, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Env(BaseSettings):
    JWT_SECRET: str
    POSTGRES_DSN: PostgresDsn
    REPOSITORIES_PATH: DirectoryPath

    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_")


env = Env()

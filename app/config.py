import os
import pathlib


class Config:
    jwt_secret = os.getenv("APP_JWT_SECRET", "foobarbaz")
    session_expiry_hours = int(os.getenv("APP_SESSION_EXPIRY_HOURS", "24"))
    postgres_url = os.getenv("APP_POSTGRES_URL", "postgresql://postgres:postgres@localhost:5432/postgres")
    repositories_path = pathlib.Path("tmp/gitogether/repositories")

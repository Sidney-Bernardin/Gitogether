from sqlalchemy.dialects.postgresql import BYTEA, TEXT, BIGINT
from sqlalchemy.orm import Mapped, mapped_column

from app.postgres import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)

    username: Mapped[str] = mapped_column(TEXT)
    password_hash: Mapped[bytes] = mapped_column(BYTEA)
    password_salt: Mapped[bytes] = mapped_column(BYTEA)

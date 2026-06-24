from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, Enum as SAEnum
from app.models.base import Base, UUIDMixin, TimestampMixin
import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    DEVELOPER = "developer"
    VIEWER = "viewer"


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.DEVELOPER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

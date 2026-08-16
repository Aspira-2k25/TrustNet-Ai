import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from services.scan_management.app.database.session import Base
from shared.constants.status import StatusEnum

class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        index=True,
        nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default=StatusEnum.SUCCESS.value,
        nullable=False
    )
    content_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    media_storage_key: Mapped[str] = mapped_column(
        String(512),
        nullable=True
    )
    raw_input: Mapped[str] = mapped_column(
        String(4096),
        nullable=True
    )
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=True
    )
    file_size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=True
    )
    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<Scan id={self.id} user={self.user_id} type={self.content_type} status={self.status}>"

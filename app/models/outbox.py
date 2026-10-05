import enum
import uuid
from datetime import datetime
from sqlalchemy import String, Enum as SAEnum, DateTime, JSON, UUID, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base

class OutboxStatus(str, enum.Enum):
    pending = "pending"
    published = "published"
    failed = "failed"
    
class Outbox(Base):
    __tablename__ = "outbox"
    
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    payload: Mapped[dict] = mapped_column(
        JSON,
        nullable=False
    )
    status: Mapped[OutboxStatus] = mapped_column(
        SAEnum(OutboxStatus, name="outbox_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=OutboxStatus.pending,
        server_default=text("'pending'::outbox_status"),
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
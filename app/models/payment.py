import enum
import uuid
from decimal import Decimal
from sqlalchemy import String, Enum as SAEnum, Numeric, JSON, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin

class PaymentCurrency(str, enum.Enum):
    rub="rub",
    usd="usd",
    eur="eur"
    
class PaymentStatus(str, enum.Enum):
    pending="pending"
    succeeded="succeeded"
    failed="failed"

class Payment(TimestampMixin, Base):
    __tablename__ = "payments"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    currency: Mapped[PaymentCurrency] = mapped_column(
        SAEnum(PaymentCurrency, 
               name="payment_currency", 
               values_callable=lambda x: [e.value for e in x]),
        nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    meta: Mapped[dict | None] = mapped_column(JSON, default=dict)
    status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus, name="payment_status", values_callable=lambda x: [e.value for e in x]), 
        default=PaymentStatus.pending,
        server_default=text("'pending'::payment_status"),) 
    idempotency_key: Mapped[uuid.UUID] = mapped_column(String(255), unique=True, nullable=False, index=True)
    webhook_url: Mapped[str] = mapped_column(String(2048), nullable=False)
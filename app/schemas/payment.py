from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.models.payment import PaymentCurrency, PaymentStatus

    
class PaymentCreate(BaseModel):
    amount: str = 0
    currency: PaymentCurrency
    description: Optional[str]
    meta: Optional[dict]
    webhook_url: str
    
    
class PaymentBase(PaymentCreate):
    status: PaymentStatus
    
    
class PaymentCreatedResponse(BaseModel):
    payment_id: str
    status: PaymentStatus
    created_at: datetime


class PaymentDetailResponse(PaymentBase):
    payment_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
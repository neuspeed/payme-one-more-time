import json
from typing import Annotated
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError


from app.core.database import get_db
from app.schemas import payment as payment_schema
from app.models.payment import Payment
from app.models.outbox import Outbox

router = APIRouter(
    prefix="/payments",
    tags=["Payments"]
)

def get_idempotency_key(idemptonecy_key: Annotated[str, Header(alias="Idempotency-Key")]):
    key = idemptonecy_key.strip()
    if not key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idempotency-Key must not be empty"
        )
    if len(key) > 255:
        raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Idempotency-Key is too long (max 255 characters)"
            )

    return key

@router.post("", response_model=payment_schema.PaymentCreatedResponse, status_code=202)
async def create_payments(
    payment: payment_schema.PaymentCreate,
    idempotency_key: str =  Depends(get_idempotency_key),
    db: AsyncSession = Depends(get_db)
):
    """Создание платежа"""
    existing_payment = await db.scalar(
        select(Payment).where(
        Payment.idempotency_key == idempotency_key
    ))
    if existing_payment:
        return payment_schema.PaymentCreatedResponse(
            payment_id=str(existing_payment.id),
            status=existing_payment.status,
            created_at=existing_payment.created_at,
        )
    
    db_payment = Payment(
        idempotency_key=idempotency_key,
        amount=payment.amount,
        currency=payment.currency,
        meta=payment.meta,
        webhook_url=payment.webhook_url,
        description=payment.description,
    )
    db.add(db_payment)
    
    try:
        await db.flush()
        db.add(
            Outbox(
                event_type="payment.created",
                payload=
                {
                    "payment_id": str(db_payment.id),
                    "payment_amount": str(db_payment.amount),
                    "payment_currency": db_payment.currency.value,
                    "payment_meta": json.dumps(payment.meta)
                }   
            )
        )
        
        await db.commit()
        
    except IntegrityError:
        db.rollback()
        existing_payment = await db.scalar(
                select(Payment).where(
                Payment.idempotency_key == idempotency_key
            ))
        if existing_payment:
            return payment_schema.PaymentCreatedResponse(
                payment_id=str(existing_payment.id),
                status=existing_payment.status,
                created_at=existing_payment.created_at,
            )
        raise
    await db.refresh(db_payment)
    return payment_schema.PaymentCreatedResponse(
        payment_id=str(db_payment.id),
        status=db_payment.status,
        created_at=db_payment.created_at)


@router.get("/{payment_id}", response_model=payment_schema.PaymentDetailResponse)
async def get_payment(
    payment_id: int, 
    db: AsyncSession = Depends(get_db)
):
    """Получение информации о платеже"""
    existing_payment = await db.scalar(
        select(Payment).where(
        Payment.id == payment_id
    ))
    if not existing_payment:
        raise HTTPException(status_code=404,detail="Payment bot found")
    return payment_schema.PaymentDetailResponse(
        payment_id=str(payment_id),
        amount=str(existing_payment.amount),
        currency=existing_payment.currency,
        description=existing_payment.description,
        meta=existing_payment.meta,
        webhook_url=existing_payment.webhook_url,
        status=existing_payment.status,
        created_at=existing_payment.created_at,
        updated_at=existing_payment.updated_at
        
    )
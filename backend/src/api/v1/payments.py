from fastapi import APIRouter, Depends, Header, Request

from src.api.dependencies import get_payment_service
from src.api.v1.schemas.payment import PaymentResponse, PaymentWebhookPayload
from src.application.services import PaymentService
from src.core import BaseResponse, ResponseGenerator
from src.domain.exceptions import AuthenticationError

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/webhook", response_model=BaseResponse[PaymentResponse])
async def handle_payment_webhook(
    request: Request,
    x_webhook_signature: str | None = Header(default=None, alias="X-Webhook-Signature"),
    payment_service: PaymentService = Depends(get_payment_service),
):
    if not x_webhook_signature:
        raise AuthenticationError("Missing X-Webhook-Signature header")

    raw_body = await request.body()
    payload = PaymentWebhookPayload.model_validate_json(raw_body)

    payment = await payment_service.process_webhook(
        raw_body=raw_body,
        signature=x_webhook_signature,
        order_id=payload.order_id,
        external_transaction_id=payload.external_transaction_id,
        status=payload.status,
        paid_amount=payload.paid_amount,
    )

    resp = PaymentResponse(
        id=payment.id,
        order_id=payment.order_id,
        provider=payment.provider,
        amount=payment.amount,
        external_id=payment.external_id,
        status=payment.status,
        paid_at=payment.paid_at,
    )
    return ResponseGenerator.answer(body=resp)

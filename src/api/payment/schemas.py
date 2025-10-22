from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

# Enums
class PaymentStatusEnum(str, Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"

class PaymentMethodEnum(str, Enum):
    CINETPAY = "CINETPAY"
    MOBILE_MONEY = "MOBILE_MONEY"
    BANK_CARD = "BANK_CARD"

# Input Schemas
class PaymentCreateInput(BaseModel):
    amount: float = Field(..., gt=0, description="Payment amount")
    currency: str = Field(..., description="Payment currency")
    payment_method: PaymentMethodEnum = Field(..., description="Payment method")
    application_id: Optional[int] = Field(None, description="Associated application ID")
    description: Optional[str] = Field(None, description="Payment description")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

class PaymentUpdateInput(BaseModel):
    status: Optional[PaymentStatusEnum] = Field(None, description="Payment status")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class PaymentFilter(BaseModel):
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Page size")
    status: Optional[PaymentStatusEnum] = Field(None, description="Filter by status")
    payment_method: Optional[PaymentMethodEnum] = Field(None, description="Filter by payment method")
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    application_id: Optional[int] = Field(None, description="Filter by application ID")
    date_from: Optional[datetime] = Field(None, description="Filter from date")
    date_to: Optional[datetime] = Field(None, description="Filter to date")
    order_by: Optional[str] = Field("created_at", description="Order by field")
    asc: Optional[str] = Field("desc", description="Sort order")

class PaymentStatusCheckInput(BaseModel):
    transaction_id: str = Field(..., description="Transaction ID to check")

class CinetpayWebhookInput(BaseModel):
    cpm_trans_id: str = Field(..., description="Transaction ID")
    cpm_trans_date: str = Field(..., description="Transaction date")
    cpm_amount: float = Field(..., description="Transaction amount")
    cpm_currency: str = Field(..., description="Transaction currency")
    cpm_payid: str = Field(..., description="Payment ID")
    cpm_payment_date: str = Field(..., description="Payment date")
    cpm_payment_time: str = Field(..., description="Payment time")
    cpm_error_message: str = Field("", description="Error message")
    cpm_phone_prefixe: str = Field("", description="Phone prefix")
    cpm_phone_number: str = Field("", description="Phone number")
    cpm_ipn_ack: str = Field("YES", description="IPN acknowledgment")
    cpm_result: str = Field(..., description="Payment result")
    cpm_trans_status: str = Field(..., description="Transaction status")
    cpm_designation: str = Field("", description="Payment designation")
    cpm_custom: str = Field("", description="Custom data")
    cpm_signature: str = Field(..., description="Payment signature")

# Output Schemas
class PaymentOut(BaseModel):
    id: int
    payment_id: str
    transaction_id: str
    amount: float
    currency: str
    status: PaymentStatusEnum
    payment_method: PaymentMethodEnum
    user_id: str
    application_id: Optional[int]
    description: Optional[str]
    metadata: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    paid_at: Optional[datetime]
    failed_at: Optional[datetime]
    refunded_at: Optional[datetime]

    class Config:
        from_attributes = True

class PaymentListOut(BaseModel):
    success: bool
    message: str
    data: list[PaymentOut]
    page: int
    number: int
    total_number: int

class PaymentStatusOut(BaseModel):
    success: bool
    message: str
    data: dict

class CinetpayWebhookOut(BaseModel):
    success: bool
    message: str
    data: dict

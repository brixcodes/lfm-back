from sqlmodel import  Field
from src.helper.model import CustomBaseUUIDModel,CustomBaseModel
from typing import  Optional
from enum import Enum

class PaymentStatusEnum(Enum):
    PENDING = "pending"  
    ACCEPTED = "accepted"  
    REFUSED = "refused"  
    CANCELLED = "cancelled"  
    ERROR = "error"  
    REPAY = "rembourse"


class Payment(CustomBaseUUIDModel,table=True):
    
    __tablename__ = "payments"
    
    transaction_id : str = Field(max_length=255, unique=True, index=True)
    product_amount : float # this is the amount from the article
    product_currency : str # this is the currency from the article
    payment_currency : str # this is the payment currency
    daily_rate : float
    usd_product_currency_rate : float
    usd_payment_currency_rate : float
    status : str = Field(default=PaymentStatusEnum.PENDING, max_length=10)
    payable_id : str
    payable_type : str
    payment_type_id : str
    payment_type : str
    

class ChannelEnum(Enum):
    
    MOBILE_MONEY = "MOBILE_MONEY"
    WALLET = "WALLET"
    CREDIT_CARD = "CREDIT_CARD"

class CinetPayPayment(CustomBaseModel, table=True):
    """Model for CinetPay payments"""
    __tablename__ = "cinetpay_payments"

    
    transaction_id: str = Field(max_length=255, unique=True, index=True)
    amount: float = Field(default=0.0, description="Amount")
    amount_received: float = Field(default=0.0, description="Amount received")
    currency: str = Field(default="XOF", max_length=3)
    status: str = Field(default=PaymentStatusEnum.PENDING, max_length=10)
    api_response_id : Optional[str] = Field(default=None, max_length=100)
    payment_url: Optional[str]   = Field(default=None, max_length=255)
    payment_token: Optional[str] = Field(default=None, max_length=255)
    error_code : Optional[str] = Field(default=None, max_length=255)
    payment_method: Optional[str] = Field(default=None, max_length=50)







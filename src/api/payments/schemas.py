from datetime import date
from pydantic import BaseModel, Field
from typing import Any, Literal, Optional

from typing import Union, TYPE_CHECKING
from src.api.job_offers.models import JobApplication
from src.helper.schemas import BaseOutSuccess,BaseOutPage

# Éviter la dépendance circulaire avec TYPE_CHECKING
if TYPE_CHECKING:
    from src.api.training.models import StudentApplication

class CinetPayInit(BaseModel):
    transaction_id: str
    amount: int
    currency: str = "XOF"
    description: str
    invoice_data : dict
    meta :str
    customer_name : Optional[str] = None
    customer_surname :  Optional[str] = None
    customer_email : Optional[str] = None
    customer_phone_number : Optional[str] = None
    customer_address : Optional[str] = None
    customer_city : Optional[str] = None
    customer_country : Optional[str] = None
    customer_state : Optional[str] = None
    customer_zip_code : Optional[str] = None

class PaymentInitInput(BaseModel):
    payable: Any 
    amount: float
    product_currency: str 
    description: str
    payment_provider: str = "CINETPAY"
    customer_name : Optional[str] = None
    customer_surname :  Optional[str] = None
    customer_email : Optional[str] = None
    customer_phone_number : Optional[str] = None
    customer_address : Optional[str] = None
    customer_city : Optional[str] = None
    customer_country : Optional[str] = None
    customer_state : Optional[str] = None
    customer_zip_code : Optional[str] = None

class WebhookPayload(BaseModel):
    cpm_site_id: str
    cpm_trans_id: str
    cpm_trans_date: str
    cpm_amount: str
    cpm_currency: str
    signature: str
    payment_method: str
    cel_phone_num: str
    cpm_phone_prefixe: str
    cpm_language: str
    cpm_version: str
    cpm_payment_config: str
    cpm_page_action: str
    cpm_custom: str
    cpm_designation: str
    cpm_error_message: str


class CinetPayCheckPaymentStatus(BaseModel):
    site_id: str
    transaction_id: str


class InitPaymentOut(BaseModel):
    payment_provider : str
    amount : float
    transaction_id : str 
    payment_link : Optional[str] = None
    notify_url : Optional[str] = None
    message : Optional[str]= None
    

class InitPaymentOutSuccess(BaseOutSuccess):
    data : InitPaymentOut
    

class PaymentFilter(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1)
    search: Optional[str] = None
    min_amount : Optional[float] = None
    max_amount : Optional[float] = None
    currency : Optional[str] = None
    status : Optional[str] = None
    date_from : Optional[date] = None
    date_to : Optional[date] = None
    order_by: Literal["created_at", "amount"] = "created_at"
    asc: Literal["asc", "desc"] = "asc"

class PaymentOut(BaseModel):
    transaction_id : str 
    product_amount : float # this is the amount from the article
    product_currency : str # this is the currency from the article
    payment_currency : str # this is the payment currency
    daily_rate : float
    usd_product_currency_rate : float
    usd_payment_currency_rate : float
    status : str 
    payable_id : str
    payable_type : str
    payment_type_id : str
    payment_type : str

class PaymentOutSuccess(BaseOutSuccess):
    data : PaymentOut
    
class PaymentPageOutSuccess(BaseOutPage):
    data : list[PaymentOut]
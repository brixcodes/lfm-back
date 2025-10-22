from typing import Any
from pydantic import BaseModel

from enum import Enum


class BaseOutPage(BaseModel):
    
    """
    Base schema for output which have pagination
    -    data : Any (the data to return)
    -    page : int (the page you have fetch)
    -    number :int (the number of record in the data)
    -    total_number : int (the total number of record found for the query)  
    -    number_page : int (the total number of page for the query)
        
    """
    
    data : Any
    page : int
    number :int
    total_number : int   
    
    
class BaseOut(BaseModel):
    
    """
    Base schema for output 
    -    message :  (message)
    -    success : bool (successful request or not)    
    """

    success : bool   
    message : str     
    
class BaseOutSuccess(BaseOut):
    
    """
    Base schema for success output 
    -    data : Any (the data to return)
    -    message :  (message)
    -    success : bool (successful request or not)    
    """

    success : bool   = True 
    message : str  
    data : Any  

class BaseOutFail(BaseOut):
    
    """
    Base schema for fail output 
    -    error_code : str (error code)
    -    message :  (message)
    -    success : bool (successful request or not)    
    """

    success : bool = False  
    message : str  
    error_code : str          

class WhatsappParameter(BaseModel):
    type : str = "text" 
    value : str = ""         
class WhatsappTemplate(BaseModel):
    templateName : str = "" 
    language : str = "en"   
    
class WhatsappMessage(BaseModel):
    
    template : WhatsappTemplate  
    phone_id : str = "" 
    parameters : list[WhatsappParameter] = []        
    
class AccessTokenType(str, Enum):
    WHATSAPP = "whatsapp"
    PESU_PAY = "pesu_pay"
    TOUPESU = "toupesu"

class LanguageType(str, Enum):
    FRENCH = "fr"
    ENGLISH = "en"    

class MESSAGE_CHANNEL(str, Enum):

    PUSHER = "pusher"
    CUSTOM_SERVICE = "custom_service"

class EMAIL_CHANNEL(str, Enum):

    SMTP = "smtp"
    MAILGUN = "mailgun"

class ErrorMessage(Enum):
    def __init__(self, value, description):
        self._value_ = value
        self.description = description

    @property
    def describe(self):
        return self.description
    
    NOT_AUTHENTICATED = ("not_authenticated", "Not Authenticated")
    INVALID_TOKEN = ("invalid_token", "Invalid Token")
    INVALID_CREDENTIALS = ("invalid_credentials", "Invalid Credentials")
    INVALID_TOKEN_TYPE = ("invalid_token_type", "Invalid Token Type")

    UNKNOWN_ERROR = ('unknown_error',"Error has occur, try latter")
    FAILED_TO_OBTAIN_USER_INFO = ('failed_to_obtain_user_info',"Failed to obtain user info")
    FAILED_TO_OBTAIN_TOKEN = ('failed_to_obtain_token',"Failed to obtain token")
    EMAIL_OR_PHONE_NUMBER_REQUIRED = ('email_or_phone_number_required',"Email or phone number required")
    

    USER_NOT_FOUND = ("user_not_found", "User not found")


    CODE_NOT_EXIST = ("code_not_exist","Code does not exist")
    CODE_ALREADY_USED= ("code_already_used","Code already used")
    CODE_HAS_EXPIRED = ("code_has_expired","Code has expired")

    USER_NOT_ACTIVE = ('user_not_active',"User is not active")
    COULD_NOT_VALIDATE_CREDENTIALS = ('could_not_validate_credentials',"Could not validate credentials")
    INCORRECT_EMAIL_OR_PASSWORD = ('in_correct_email_or_password',"Incorrect email or password")
    EMAIL_ALREADY_TAKEN = ('email_already_token',"Email already taken")
    EMAIL_NOT_FOUND = ('email_not_found',"User email not found")
    PASSWORD_NOT_CORRECT = ('password_not_correct',"The password is not correct")

    
    REFRESH_TOKEN_NOT_FOUND = ('refresh_token_not_found',"Refresh token not found")
    REFRESH_TOKEN_HAS_EXPIRED = ('refresh_token_has_expired',"Refresh token has expired")

    SOME_THING_WENT_WRONG = ('something_went_wrong',"Something went wrong try later")
    TOUPESU_USER_NOT_FOUND = ('toupesu_user_not_found',"Toupesu user not found")

    ACCESS_DENIED = ('access_denied',"Access denied")
    SERVER_ERROR = ('server_error',"Server error")
    PROVIDER_NOT_SUPPORTED = ('provider_not_supported',"Provider not supported")   
    
    CATEGORY_NOT_FOUND = ('category_not_found',"Category not found")
    CATEGORY_ALREADY_EXISTS = ('category_already_exists',"Category already exists")
    POST_NOT_FOUND = ('post_not_found',"Post not found")
    POST_SECTION_NOT_FOUND = ('post_section_not_found',"Post section not found")
    POST_ALREADY_EXISTS = ('post_already_exists',"Post already exists")
    
    # Job Offer Errors
    JOB_OFFER_NOT_FOUND = ('job_offer_not_found',"Job offer not found")
    JOB_OFFER_REFERENCE_TAKEN = ('job_offer_reference_taken',"Job offer reference already exists")
    
    # Job Application Errors
    JOB_APPLICATION_NOT_FOUND = ('job_application_not_found',"Job application not found")
    
    # Job Attachment Errors
    JOB_ATTACHMENT_NOT_FOUND = ('job_attachment_not_found',"Job attachment not found")
    
    JOB_OFFER_CLOSED = ('job_offer_closed',"Job offer is closed")
    
    # OTP Errors
    INVALID_OTP_OR_APPLICATION_NOT_FOUND = ('invalid_otp_or_application_not_found',"Invalid OTP code or application not found")
    
    JOB_ATTACHMENT_REQUIRED = ('job_attachment_required',"Job attachment is required")
    
    PAYMENT_NOT_FOUND = ('payment_not_found',"Payment not found")
    PAYMENT_ALREADY_EXISTS = ('payment_already_exists',"Payment already exists")
    
    PAYMENT_METHOD_NOT_FOUND = ('payment_method_not_found',"Payment method not found")
    PAYMENT_METHOD_ALREADY_EXISTS = ('payment_method_already_exists',"Payment method already exists")
    
    PAYMENT_METHOD_TYPE_NOT_FOUND = ('payment_method_type_not_found',"Payment method type not found")
    
    CAN_NOT_DELETE_SUPER_ADMIN = ('can_not_delete_super_admin',"Can not delete super admin")
    
    PAYMENT_INITIATION_FAILED = ('payment_initiation_failed',"Payment initiation failed")
    
    # Training Errors
    TRAINING_NOT_FOUND = ('training_not_found',"Training not found")
    TRAINING_SESSION_NOT_FOUND = ('training_session_not_found',"Training session not found")
    
    # Student Application Errors
    STUDENT_APPLICATION_NOT_FOUND = ('student_application_not_found',"Student application not found")
    STUDENT_ATTACHMENT_NOT_FOUND = ('student_attachment_not_found',"Student attachment not found")
    SPECIALTY_NOT_FOUND = ('specialty_not_found',"Specialty not found")
    
    CANNOT_APPROVE_UNPAID_APPLICATION =("cannot_approve_unpaid_application","cannot approve unpaid application")
    
    REGISTRATION_CLOSED = ('registration_closed',"Registration is closed")
    
    NO_AVAILABLE_SLOTS = ('no_available_slots',"No available slots")
    SESSION_NOT_OPEN = ('session_not_open',"Session is not open")
    
    ORGANIZATION_CENTER_NOT_FOUND = ('organization_center_not_found',"Organization center not found")
    ORGANIZATION_CENTER_EMAIL_ALREADY_EXISTS = ('organization_center_email_already_exists',"Organization center email already exists")
    ORGANIZATION_CENTER_NAME_ALREADY_EXISTS = ('organization_center_name_already_exists',"Organization center name already exists")
    ORGANIZATION_CENTER_EMAIL_NOT_FOUND = ('organization_center_email_not_found',"Organization center email not found")
    ORGANIZATION_CENTER_NAME_NOT_FOUND = ('organization_center_name_not_found',"Organization center name not found")
    ORGANIZATION_CENTER_CONTACT_NOT_FOUND = ('organization_center_contact_not_found',"Organization center contact not found")
    ORGANIZATION_CENTER_CONTACT_ALREADY_EXISTS = ('organization_center_contact_already_exists',"Organization center contact already exists")
    YOU_ARE_NOT_REGISTERED_FOR_THIS_TRAINING_SESSION = ('you_are_not_registered_for_this_training_session',"You are not registered for this training session")
    
    TRAINING_FEE_ALREADY_PAID = ('training_fee_already_paid',"Training fee already paid")
    
    TRAINING_FEE_INSTALLMENT_AMOUNT_TOO_SMALL = ('training_fee_installment_amount_too_small',"Training fee installment amount too small")
    
    NO_ROLE_FOUND = ('no_role_found',"No role found")
    
    ROLE_NOT_FOUND = ('role_not_found',"Role not found")
    def __str__(self):
        return self.value

import os
from pydantic_settings import BaseSettings
from pydantic import ConfigDict, model_validator,EmailStr, BeforeValidator,AnyUrl,computed_field,HttpUrl
from typing import ClassVar, Literal,Annotated,Any
from typing_extensions import Self
import secrets
from kombu import Queue

# dmlnfn
#
def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)

def route_task(name, args, kwargs, options, task=None, **kw):
    if ":" in name:
        queue, _ = name.split(":")
        return {"queue": queue}
    return {"queue": "lafaom_default"}

class Settings(BaseSettings):
    
    PROJECT_NAME: str = "La'akam"
    ENV: Literal["development", "staging", "production"] = "development"
    
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    
    SECRET_KEY: str = secrets.token_urlsafe(32) 
    ALGORITHM: str = "HS256"
    
    ACCESS_TOKEN_EXPIRE_MINUTES : int = 3600
    REFRESH_TOKEN_EXPIRE_MINUTES : int = 3600
    OTP_CODE_EXPIRE_MINUTES : int = 30
    
    ## Sentry Debugging url 
    SENTRY_DSN: HttpUrl | None = None
    
    ## Allow Cors origins
    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []
    
    @computed_field  
    @property
    def all_cors_origins(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS] 
    
    ## Notification System
    EMAIL_CHANNEL : Literal["smtp","mailgun"] = "smtp"
    
    
    ## Email Parameters
    EMAILS_FROM_EMAIL: EmailStr | None = None
    EMAILS_FROM_NAME: str | None = None
    
    @model_validator(mode="after")
    def _set_default_emails_from(self) -> Self:
        if not self.EMAILS_FROM_NAME:
            self.EMAILS_FROM_NAME = self.PROJECT_NAME
        return self
    
    ## Credential to connect to the SMTP Server
    SMTP_ENCRYPTION: Literal["TLS", "SSL"] = "SSL"
    SMTP_PORT: int = 587
    SMTP_HOST: str | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    

    ## Credential to connect to the Mailgun Server
    MAILGUN_DOMAIN : str =""
    MAILGUN_SECRET : str =""
    MAILGUN_ENDPOINT : str ="api.eu.mailgun.net"


    
    ## Credential to connect to Firebase Cloud Messaging for push notification
    FCM_SERVER_KEY:str = ""
    
    
    
    #Prefer storage location
    STORAGE_LOCATION: Literal["local","S3"] = "local"  #local,S3
    
    
    #Max file upload size (20MB for PDF documents)
    MAX_FILE_SIZE: int = 20971520
    
    
    ## Credential to connect to AWS S3 Bucket
    AWS_ACCESS_KEY_ID : str = ""
    AWS_SECRET_ACCESS_KEY : str = ""
    AWS_REGION : str = "us-east-1"
    AWS_BUCKET_NAME : str = "your-bucket-name"
    
    MOODLE_API_URL : str = "https://moodle.example.com"
    MOODLE_API_TOKEN : str = ""

    ## Credential to connect to the CinetPay Server
    # Les valeurs sont chargées depuis le fichier .env
    CINETPAY_API_KEY: str = ""
    CINETPAY_SITE_ID: str = ""
    CINETPAY_SECRET_KEY: str = ""
    CINETPAY_NOTIFY_URL: str = "https://api.lafaom-mao.org/api/v1/payments/cinetpay/notify"
    CINETPAY_RETURN_URL: str = "https://api.lafaom-mao.org/"
    CINETPAY_CURRENCY: str = "XAF"  # XAF pour le compte CinetPay
    
    ## CinetPay Payment Channels Configuration
    # Canaux de paiement disponibles selon la documentation CinetPay
    # Format correct : "ALL" ou liste séparée par virgules
    CINETPAY_CHANNELS: str = "ALL"  # Utilise tous les canaux disponibles
    
    ## CinetPay Card Payments Configuration
    CINETPAY_ENABLE_CARD_PAYMENTS: bool = True
    CINETPAY_ENABLE_VISA: bool = True
    CINETPAY_ENABLE_MASTERCARD: bool = True
    CINETPAY_VISA_SECURED: bool = True
    CINETPAY_MASTERCARD_SECURED: bool = True
    
    ## CinetPay Card Payment Settings
    CINETPAY_CARD_MIN_AMOUNT: int = 100  # Montant minimum pour les paiements par carte (100 XAF = ~0.15€)
    CINETPAY_CARD_MAX_AMOUNT: int = 50000000  # Montant maximum pour les paiements par carte (500,000 XAF)
    CINETPAY_CARD_CURRENCY: str = "XAF"  # Devise pour les paiements par carte (Cameroun)
    
    CURRENCY_API_KEY : str | None = None
    CURRENCY_API_URL: str | None = None
    
    ## Frontend and API URLs
    FRONTEND_URL: str = "https://lafaom-mao.org"
    API_BASE_URL: str = "https://api.lafaom-mao.org"
    
    ## The Redis Cache turn around time
    CACHE_TTL:int   = 3600
    
    ## Redis cache url
    REDIS_CACHE_URL:str = "redis://127.0.0.1:6379/0"
    
    ## Celery Broker and backend result url 
    CELERY_BROKER_URL: str = "redis://127.0.0.1:6379/0"
    CELERY_RESULT_BACKEND: str =  "redis://127.0.0.1:6379/0"

    JWK_ISS : str = "lafoam.com"
    JWK_ALGORITHM : str = "RS256"

    CELERY_BEAT_SCHEDULE: dict = {
        # "task-schedule-work": {
        #     "task": "task_schedule_work",
        #     "schedule": 5.0,  # five seconds
        # },
        
        # "task-schedule-work": {
        #     "task": "task_schedule_work",
        #     "schedule": crontab(minute="*/1"),
        # },
        # "task-schedule-work": {
        #     "task": "task_schedule_work",
        #     "schedule": crontab(minute="*/1"),
        # },
        
    }
    
    REDIS_NAMESPACE:str = "lafaom"

    CELERY_TASK_DEFAULT_QUEUE: str = "lafaom_default"

    # Force all queues to be explicitly listed in `CELERY_TASK_QUEUES` to help prevent typos
    CELERY_TASK_CREATE_MISSING_QUEUES: bool = False

    CELERY_TASK_QUEUES: list[Queue]  = [
        Queue("lafaom_default"),
        Queue("lafaom_high_priority"),
        Queue("lafaom_low_priority"),
    ]

    CELERY_TASK_ROUTES: ClassVar[tuple] = (route_task,)
    


    model_config = ConfigDict(
        env_file = ".env",
        extra="ignore"
    )




settings = Settings()

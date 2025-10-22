from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError,HTTPException
from fastapi.responses import JSONResponse
from src.api.auth.utils import rotate_key
from src.config import settings
from src.api.user.router import router as user_router
from src.api.blog.router import router as blog_router
from src.api.job_offers.router import router as job_offers_router
from src.api.payments.router import router as payments_router
from src.api.auth.router import router as auth_router
from src.api.training.routers import router as training_router
from src.api.system.router import router as system_router
from src.api.system.dashboard import router as dashboard_router
from src.api.cabinet.router import router as cabinet_router

import firebase_admin
from firebase_admin import credentials
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import sentry_sdk
from src.celery_utils import create_celery
from src.helper.schemas import BaseOutFail, ErrorMessage

# Initialize Firebase Admin SDK
if firebase_admin._apps:
    firebase_admin.delete_app(firebase_admin.get_app())
cred = credentials.Certificate("src/lafaom.json")
firebase_admin.initialize_app(credential=cred)

if settings.SENTRY_DSN and settings.ENV != "development":
    sentry_sdk.init(
        dsn= settings.SENTRY_DSN,
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for tracing.
        traces_sample_rate=1.0,
        _experiments={
            # Set continuous_profiling_auto_start to True
            # to automatically start the profiler on when
            # possible.
            "continuous_profiling_auto_start": True,
        },)



app = FastAPI(title=settings.PROJECT_NAME)
celery = create_celery()
app.celery_app = celery

base_url = "/api/v1"

# CORS configuration
origins = [
    "https://www.lafaom-mao.org",
    "https://lafaom-bioforce.vercel.app",
    "https://lafaom-bioforce-git-main-nanyang-brices-projects-daa29c6d.vercel.app",
    "https://lafaom-bioforce-hi1zi9iri-nanyang-brices-projects-daa29c6d.vercel.app",
    "https://lafaom-mao.org",
    "https://lafaom.netlify.app",
    "https://admin.lafaom-mao.org",
    "http://admin.lafaom-mao.org",
    "http://localhost:5500",
    "http://localhost",
    "https://vitrine-lafaom.vercel.app",
    "http://localhost:4200",
    "http://localhost:5173",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:4200",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:5500",
    "https://vitrine-lafaom.vercel.app",
    "https://www.lafaom.vertex-cam.com/",
    "https://lafaom.vertex-cam.com",
]

app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Accept",
        "Accept-Language",
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "Origin",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers",
    ],
    expose_headers=["*"],
)

app.mount("/static", StaticFiles(directory="src/static"), name="static")

app.include_router(auth_router, prefix=base_url + "/auth", tags=["Auth"])
app.include_router(user_router, prefix=base_url )
app.include_router(blog_router, prefix=base_url )
app.include_router(job_offers_router, prefix=base_url )
app.include_router(training_router, prefix=base_url )
app.include_router(payments_router, prefix=base_url + "/payments", tags=["Payments"])
app.include_router(system_router, prefix=base_url + "/system", tags=["System"])
app.include_router(dashboard_router, prefix=base_url + "/dashboard", tags=["Dashboard"])
app.include_router(cabinet_router, prefix=base_url + "/cabinet-application")

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    simplified_errors = [{"loc": err["loc"], "msg": err["msg"]} for err in errors]
    try :
        return JSONResponse(
            status_code=422,
            content= {   
                        "message": "Validation error",
                        "error_code" : "validation_error",
                        "data" : exc.body,
                        "error":simplified_errors,
                        "success": False
                    }, 
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=422,
            content= {"message": "Validation error","error_code" : "validation_error","error":simplified_errors,"success": False}
        )
    

@app.exception_handler(HTTPException)
async def validation_exception_handler(request: Request, exc: HTTPException):
    
    
    
    if isinstance(exc.detail, str):
        if exc.status_code == 403:
            return JSONResponse(
                status_code=403,
                content=BaseOutFail(
                    message=ErrorMessage.NOT_AUTHENTICATED.description,
                    error_code=ErrorMessage.NOT_AUTHENTICATED.value).model_dump()
            )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail" : exc.detail}, 
        )
    else:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail, 
        )
        


@app.get("/", tags=["Root"])
async def root() -> dict:
    
    return {
        "message": "Welcome to Lafaom Mao API ",
        "documentation": "/docs",
        "Environment": settings.ENV
    }

@app.get("/health/database", tags=["Health"])
async def database_health() -> dict:
    """Check database table existence"""
    try:
        from src.database import get_session_async
        from sqlalchemy import text
        
        async for session in get_session_async():
            # Check if post_categories table exists
            result = await session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'post_categories'
                );
            """))
            post_categories_exists = result.scalar()
            
            return {
                "status": "healthy",
                "database": "connected",
                "tables": {
                    "post_categories": post_categories_exists,
                    "users": True,  # Assuming users table exists
                }
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }  

@app.on_event("startup")
async def startup_event():
    #wait rotate_key()
    pass
from fastapi import APIRouter

from src.api.training.routers.training import router as training_router
from src.api.training.routers.student_application import router as student_application_router
from src.api.training.routers.specialty import router as specialty_router
from src.api.training.routers.reclamation import router as reclamation_router

router = APIRouter()

router.include_router(training_router)
router.include_router(student_application_router)
router.include_router(specialty_router)
router.include_router(reclamation_router)
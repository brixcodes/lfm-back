# Import all services
from .specialty import SpecialtyService
from .training import TrainingService  
from .student_application import StudentApplicationService
from .reclamation import ReclamationService

# Export all services
__all__ = [
    "SpecialtyService",
    "TrainingService",
    "StudentApplicationService", 
    "ReclamationService",
]
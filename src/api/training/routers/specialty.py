from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status
from src.api.auth.utils import check_permissions
from src.api.user.models import PermissionEnum, User
from src.helper.schemas import BaseOutFail
from src.api.training.services import SpecialtyService
from src.api.training.schemas import (
    SpecialtyCreateInput,
    SpecialtyUpdateInput,
    SpecialtyOutSuccess,
    SpecialtyListOutSuccess,
    SpecialtiesPageOutSuccess,
    SpecialtyFilter,
)
from src.api.training.dependencies import get_specialty

router = APIRouter()

# Specialty CRUD Endpoints
@router.get("/specialties", response_model=SpecialtiesPageOutSuccess, tags=["Specialty"])
async def list_specialties(
    filters: Annotated[SpecialtyFilter, Query(...)],
    specialty_service: SpecialtyService = Depends(),
):
    """Get paginated list of specialties"""
    specialties, total = await specialty_service.list_specialties(filters)
    return {
        "data": specialties,
        "page": filters.page,
        "number": len(specialties),
        "total_number": total,
        "message": "Specialties fetched successfully"
    }


@router.post("/specialties", response_model=SpecialtyOutSuccess, tags=["Specialty"])
async def create_specialty(
    input: SpecialtyCreateInput,
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_CREATE_TRAINING]))],
    specialty_service: SpecialtyService = Depends(),
):
    """Create a new specialty"""
    # Check if specialty with same name already exists
    existing_specialty = await specialty_service.get_specialty_by_name(input.name)
    if existing_specialty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message="Specialty with this name already exists",
                error_code="SPECIALTY_NAME_ALREADY_EXISTS"
            ).model_dump()
        )
    
    specialty = await specialty_service.create_specialty(input)
    return {"message": "Specialty created successfully", "data": specialty}


@router.get("/specialties/{specialty_id}", response_model=SpecialtyOutSuccess, tags=["Specialty"])
async def get_specialty_route(
    specialty_id: int,
    specialty=Depends(get_specialty),
):
    """Get specialty by ID"""
    return {"message": "Specialty fetched successfully", "data": specialty}


@router.put("/specialties/{specialty_id}", response_model=SpecialtyOutSuccess, tags=["Specialty"])
async def update_specialty_route(
    specialty_id: int,
    input: SpecialtyUpdateInput,
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_UPDATE_TRAINING]))],
    specialty=Depends(get_specialty),
    specialty_service: SpecialtyService = Depends(),
):
    """Update specialty"""
    # Check if another specialty with same name exists
    existing_specialty = await specialty_service.get_specialty_by_name(input.name)
    if existing_specialty and existing_specialty.id != specialty.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message="Specialty with this name already exists",
                error_code="SPECIALTY_NAME_ALREADY_EXISTS"
            ).model_dump()
        )
    
    specialty = await specialty_service.update_specialty(specialty, input)
    return {"message": "Specialty updated successfully", "data": specialty}


@router.delete("/specialties/{specialty_id}", response_model=SpecialtyOutSuccess, tags=["Specialty"])
async def delete_specialty_route(
    specialty_id: int,
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_DELETE_TRAINING]))],
    specialty=Depends(get_specialty),
    specialty_service: SpecialtyService = Depends(),
):
    """Delete specialty (soft delete)"""
    specialty = await specialty_service.delete_specialty(specialty)
    return {"message": "Specialty deleted successfully", "data": specialty}


@router.get("/specialties/active/all", response_model=SpecialtyListOutSuccess, tags=["Specialty"])
async def get_active_specialties(
    specialty_service: SpecialtyService = Depends(),
):
    """Get all active specialties for dropdown lists"""
    specialties = await specialty_service.get_all_active_specialties()
    return {"data": specialties, "message": "Active specialties fetched successfully"}
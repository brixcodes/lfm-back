from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Annotated

from src.api.auth.utils import check_permissions, get_current_active_user
from src.api.system.dependencies import get_organization_center
from src.api.user.models import PermissionEnum, User
from src.helper.schemas import BaseOutFail, ErrorMessage
from src.api.system.service import OrganizationCenterService
from src.api.system.schemas import (
    CreateOrganizationCenterInput,
    UpdateOrganizationCenterInput,
    UpdateOrganizationStatusInput,
    OrganizationCenterOutSuccess,
    OrganizationCenterListOutSuccess,
    OrganizationCentersPageOutSuccess,
    OrganizationCenterFilter,
    OrganizationCenterListInput,
)
from src.api.system.models import OrganizationCenter

router = APIRouter()

@router.get("/organization-centers", response_model=OrganizationCentersPageOutSuccess, tags=["Organization Centers"])
async def read_organization_centers_list(
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_VIEW_ORGANIZATION_CENTER]))],
    filter_query: Annotated[OrganizationCenterFilter, Query(...)],
    org_service: OrganizationCenterService = Depends()
):
    """Get paginated list of organization centers with filtering"""
    
    organizations, counted = await org_service.get(org_filter=filter_query)
    
    return {
        "data": organizations,
        "page": filter_query.page,
        "number": len(organizations),
        "total_number": counted,
        "message": "Organization Centers fetched successfully"
    }

@router.post("/organization-centers", response_model=OrganizationCenterOutSuccess, tags=["Organization Centers"])
async def create_organization_center(
    organization_create_input: CreateOrganizationCenterInput,
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_CREATE_ORGANIZATION_CENTER]))],
    org_service: OrganizationCenterService = Depends()
):
    """Create a new organization center"""
    
    # Check if organization with same name already exists
    existing_org = await org_service.get_by_name(organization_create_input.name)
    if existing_org:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message=ErrorMessage.ORGANIZATION_CENTER_NAME_ALREADY_EXISTS.description,
                error_code=ErrorMessage.ORGANIZATION_CENTER_NAME_ALREADY_EXISTS.value
            ).model_dump()
        )
    
    # Check if organization with same email already exists (if email provided)
    if organization_create_input.email:
        existing_org_email = await org_service.get_by_email(organization_create_input.email)
        if existing_org_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=BaseOutFail(
                    message=ErrorMessage.ORGANIZATION_CENTER_EMAIL_ALREADY_EXISTS.description,
                    error_code=ErrorMessage.ORGANIZATION_CENTER_EMAIL_ALREADY_EXISTS.value
                ).model_dump()
            )

    organization = await org_service.create(organization_create_input)
    return {"data": organization, "message": "Organization Center created successfully"}

@router.get("/organization-centers/{organization_id}", response_model=OrganizationCenterOutSuccess, tags=["Organization Centers"])
async def read_organization_center_by_id(
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_VIEW_ORGANIZATION_CENTER]))],
    organization: Annotated[OrganizationCenter, Depends(get_organization_center)]
):
    """Get organization center by ID"""
    
    return {"data": organization, "message": "Organization Center fetched successfully"}

@router.put("/organization-centers/{organization_id}", response_model=OrganizationCenterOutSuccess, tags=["Organization Centers"])
async def update_organization_center(
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_UPDATE_ORGANIZATION_CENTER]))],
    organization_id: int,
    organization_update_input: UpdateOrganizationCenterInput,
    organization: Annotated[OrganizationCenter, Depends(get_organization_center)],
    org_service: OrganizationCenterService = Depends(),
):
    """Update organization center"""
    
    # Check if another organization with same name exists
    existing_org = await org_service.get_by_name(organization_update_input.name)
    if existing_org and existing_org.id != organization.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message=ErrorMessage.ORGANIZATION_CENTER_NAME_ALREADY_EXISTS.description,
                error_code=ErrorMessage.ORGANIZATION_CENTER_NAME_ALREADY_EXISTS.value
            ).model_dump()
        )
    
    # Check if another organization with same email exists (if email provided)
    if organization_update_input.email:
        existing_org_email = await org_service.get_by_email(organization_update_input.email)
        if existing_org_email and existing_org_email.id != organization.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=BaseOutFail(
                    message=ErrorMessage.ORGANIZATION_CENTER_EMAIL_ALREADY_EXISTS.description,
                    error_code=ErrorMessage.ORGANIZATION_CENTER_EMAIL_ALREADY_EXISTS.value
                ).model_dump()
            )

    organization = await org_service.update(organization_id, organization_update_input)
    
    return {"data": organization, "message": "Organization Center updated successfully"}

@router.post("/organization-centers/change-status/{organization_id}", response_model=OrganizationCenterOutSuccess, tags=["Organization Centers"])
async def update_organization_center_status(
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_UPDATE_ORGANIZATION_CENTER]))],
    organization_id: int,
    status_update_input: UpdateOrganizationStatusInput,
    organization: Annotated[OrganizationCenter, Depends(get_organization_center)],
    org_service: OrganizationCenterService = Depends(),
):
    """Update organization center status"""
    
    organization = await org_service.update_status(organization_id, status_update_input.status)
    
    return {"data": organization, "message": "Organization Center status updated successfully"}

@router.delete("/organization-centers/{organization_id}", response_model=OrganizationCenterOutSuccess, tags=["Organization Centers"])
async def delete_organization_center(
    organization_id: int,
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_DELETE_ORGANIZATION_CENTER]))],
    organization: Annotated[OrganizationCenter, Depends(get_organization_center)],
    org_service: OrganizationCenterService = Depends(),
):
    """Soft delete organization center"""
    
    organization = await org_service.delete(organization_id)
    return {"data": organization, "message": "Organization Center deleted successfully"}

@router.post("/organization-centers/internal", response_model=OrganizationCenterListOutSuccess, tags=["Organization Centers"])
async def read_organization_centers_internal(
    input: OrganizationCenterListInput,
    org_service: OrganizationCenterService = Depends(),
):
    """Get multiple organization centers by ID list for internal use"""
    
    organizations = await org_service.get_organizations_by_id_list(org_ids=input.organization_center_ids)
    return {"data": organizations, "message": "Organization Centers list fetched successfully"}



@router.get("/organization-centers/location/{country_code}", response_model=OrganizationCenterListOutSuccess, tags=["Organization Centers"])
async def read_organization_centers_by_location(
    country_code: str,
    city: str = Query(None),
    org_service: OrganizationCenterService = Depends()
):
    """Get organization centers by location"""
    
    organizations = await org_service.get_by_location(country_code=country_code, city=city)
    return {"data": organizations, "message": "Organization Centers fetched successfully"}

@router.get("/organization-centers/{organization_id}/public", response_model=OrganizationCenterOutSuccess, tags=["Organization Centers"])
async def read_organization_center_public(
    organization_id: int,
    org_service: OrganizationCenterService = Depends()
):
    """Get organization center by ID (public access)"""
    
    organization = await org_service.get_by_id(organization_id)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=BaseOutFail(
                message=ErrorMessage.ORGANIZATION_CENTER_NOT_FOUND.description,
                error_code=ErrorMessage.ORGANIZATION_CENTER_NOT_FOUND.value
            ).model_dump()
        )
    
    return {"data": organization, "message": "Organization Center fetched successfully"}


from fastapi import HTTPException, Depends, status

from src.helper.schemas import BaseOutFail, ErrorMessage
from src.api.system.service import OrganizationCenterService


async def get_organization_center(organization_id: int, org_service: OrganizationCenterService = Depends()):
    
    organization = await org_service.get_by_id(organization_id)
    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=BaseOutFail(
                message=ErrorMessage.ORGANIZATION_CENTER_NOT_FOUND.description,
                error_code=ErrorMessage.ORGANIZATION_CENTER_NOT_FOUND.value
            ).model_dump()
        )
    return organization
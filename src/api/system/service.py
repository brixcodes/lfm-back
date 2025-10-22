from datetime import datetime, timezone
from typing import List
from fastapi import Depends
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from src.api.system.schemas import OrganizationCenterFilter
from src.database import get_session_async
from src.api.system.models import OrganizationCenter, OrganizationStatusEnum, OrganizationTypeEnum
from sqlmodel import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

class OrganizationCenterService:
    def __init__(self, session: AsyncSession = Depends(get_session_async)) -> None:
        self.session = session

    async def get(self, org_filter: OrganizationCenterFilter):
        """Get paginated list of organization centers with filtering"""
        
        statement = (
            select(OrganizationCenter)
            .where(OrganizationCenter.delete_at.is_(None))
        )

        count_query = (
            select(func.count(OrganizationCenter.id))
            .where(OrganizationCenter.delete_at.is_(None))
        )

        # Apply search filter
        if org_filter.search is not None:
            search_filter = or_(
                OrganizationCenter.name.contains(org_filter.search),
                OrganizationCenter.email.contains(org_filter.search),
                OrganizationCenter.city.contains(org_filter.search),
                OrganizationCenter.address.contains(org_filter.search),
                OrganizationCenter.telephone_number.contains(org_filter.search),
                OrganizationCenter.mobile_number.contains(org_filter.search),
                OrganizationCenter.description.contains(org_filter.search),
            )
            statement = statement.where(search_filter)
            count_query = count_query.where(search_filter)
        
        # Apply status filter
        if org_filter.status is not None:
            statement = statement.where(OrganizationCenter.status == org_filter.status)
            count_query = count_query.where(OrganizationCenter.status == org_filter.status)
        
        # Apply organization type filter
        if org_filter.organization_type is not None:
            statement = statement.where(OrganizationCenter.organization_type == org_filter.organization_type)
            count_query = count_query.where(OrganizationCenter.organization_type == org_filter.organization_type)
        
        # Apply country code filter
        if org_filter.country_code is not None:
            statement = statement.where(OrganizationCenter.country_code == org_filter.country_code)
            count_query = count_query.where(OrganizationCenter.country_code == org_filter.country_code)

        # Apply city filter
        if org_filter.city is not None:
            statement = statement.where(OrganizationCenter.city == org_filter.city)
            count_query = count_query.where(OrganizationCenter.city == org_filter.city)

        # Apply ordering
        if org_filter.order_by == "created_at":
            if org_filter.asc == "asc":
                statement = statement.order_by(OrganizationCenter.created_at)
            else:
                statement = statement.order_by(OrganizationCenter.created_at.desc())
        elif org_filter.order_by == "updated_at":
            if org_filter.asc == "asc":
                statement = statement.order_by(OrganizationCenter.updated_at)
            else:
                statement = statement.order_by(OrganizationCenter.updated_at.desc())
        elif org_filter.order_by == "name":
            if org_filter.asc == "asc":
                statement = statement.order_by(OrganizationCenter.name)
            else:
                statement = statement.order_by(OrganizationCenter.name.desc())

        # Get total count
        total_count = await self.session.execute(count_query)
        total_count = total_count.scalar_one()

        # Apply pagination
        statement = statement.offset((org_filter.page - 1) * org_filter.page_size).limit(
            org_filter.page_size
        )
        result = await self.session.execute(statement)
        organizations = result.scalars().all()

        return organizations, total_count

    async def create(self, org_create_input):
        """Create a new organization center"""
        organization = OrganizationCenter(**org_create_input.model_dump())
        self.session.add(organization)
        await self.session.commit()
        await self.session.refresh(organization)
        return organization

    async def get_by_id(self, org_id: int):
        """Get organization center by ID"""
        statement = select(OrganizationCenter).where(
            OrganizationCenter.id == org_id
        ).where(OrganizationCenter.delete_at.is_(None))
        result = await self.session.execute(statement)
        organization = result.scalars().first()
        return organization

    async def get_by_name(self, org_name: str):
        """Get organization center by name"""
        statement = select(OrganizationCenter).where(
            OrganizationCenter.name == org_name
        ).where(OrganizationCenter.delete_at.is_(None))
        result = await self.session.execute(statement)
        organization = result.scalars().first()
        return organization

    async def get_by_email(self, org_email: str):
        """Get organization center by email"""
        statement = select(OrganizationCenter).where(
            OrganizationCenter.email == org_email
        ).where(OrganizationCenter.delete_at.is_(None))
        result = await self.session.execute(statement)
        organization = result.scalars().first()
        return organization

    async def get_organizations_by_id_list(self, org_ids: List[int]):
        """Get multiple organization centers by ID list"""
        statement = select(OrganizationCenter).where(
            OrganizationCenter.id.in_(org_ids)
        ).where(OrganizationCenter.delete_at.is_(None))
        result = await self.session.execute(statement)
        organizations = result.scalars().all()
        return organizations

    async def update(self, org_id: int, org_update_input):
        """Update organization center"""
        statement = select(OrganizationCenter).where(OrganizationCenter.id == org_id)
        result = await self.session.execute(statement)
        organization = result.scalars().one()
        
        for key, value in org_update_input.model_dump().items():
            setattr(organization, key, value)
        
        self.session.add(organization)
        await self.session.commit()
        await self.session.refresh(organization)
        return organization

    async def update_status(self, org_id: int, status: OrganizationStatusEnum):
        """Update organization center status"""
        statement = select(OrganizationCenter).where(OrganizationCenter.id == org_id)
        result = await self.session.execute(statement)
        organization = result.scalars().one()
        organization.status = status
        self.session.add(organization)
        await self.session.commit()
        await self.session.refresh(organization)
        return organization

    async def delete(self, org_id: int):
        """Soft delete organization center"""
        statement = select(OrganizationCenter).where(OrganizationCenter.id == org_id)
        result = await self.session.execute(statement)
        organization = result.scalars().one()
        organization.status = OrganizationStatusEnum.DELETED
        organization.delete_at = datetime.now(timezone.utc)
        self.session.add(organization)
        await self.session.commit()
        await self.session.refresh(organization)
        return organization

    async def get_all_active(self):
        """Get all active organization centers"""
        statement = select(OrganizationCenter).where(
            OrganizationCenter.status == OrganizationStatusEnum.ACTIVE
        ).where(OrganizationCenter.delete_at.is_(None))
        result = await self.session.execute(statement)
        organizations = result.scalars().all()
        return organizations

    async def get_by_location(self, country_code: str = None, city: str = None):
        """Get organization centers by location"""
        statement = select(OrganizationCenter).where(
            OrganizationCenter.delete_at.is_(None)
        )
        
        if country_code:
            statement = statement.where(OrganizationCenter.country_code == country_code)
        if city:
            statement = statement.where(OrganizationCenter.city == city)
            
        result = await self.session.execute(statement)
        organizations = result.scalars().all()
        return organizations

    async def get_by_type(self, org_type: OrganizationTypeEnum):
        """Get organization centers by type"""
        statement = select(OrganizationCenter).where(
            OrganizationCenter.organization_type == org_type
        ).where(OrganizationCenter.delete_at.is_(None))
        result = await self.session.execute(statement)
        organizations = result.scalars().all()
        return organizations
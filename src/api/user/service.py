from datetime import date, datetime, timezone
from typing import List
from fastapi import Depends
from sqlalchemy import func
from sqlalchemy.orm import selectinload , aliased, with_expression
from src.api.user.schemas import UpdateUserInput, UserFilter
from src.database import get_session_async
from src.api.user.models import (Address, AddressTypeEnum, CivilityEnum, PermissionEnum, ProfessionStatus, SchoolCurriculum, User, UserPermission, UserRole, Role, RoleEnum, UserStatusEnum, UserTypeEnum)
from src.api.auth.schemas import UpdateAddressInput, UpdateCurriculumInput, UpdateDeviceInput, UpdateProfessionStatusInput,  UpdateUserProfile
from sqlmodel import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
import re

from src.helper.notifications import SendPasswordNotification
from src.helper.moodle import MoodleService

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    def __init__(self, session: AsyncSession = Depends(get_session_async)) -> None:
        self.session = session

    async def get(self,user_filter : UserFilter):
        
        statement = (
            select(
                User
            )
            .where(User.delete_at.is_(None))
        )

        count_query = (
            select(func.count(User.id))
            .where(User.delete_at.is_(None))
        )

        if user_filter.search is not None:
            statement = statement.where(
                or_(
                    User.first_name.contains(user_filter.search),
                    User.last_name.contains(user_filter.search),
                    User.email.contains(user_filter.search),
                    User.mobile_number.contains(user_filter.search),
                    User.fix_number.contains(user_filter.search),
                    User.country_code.contains(user_filter.search),
                )
            )
            count_query = count_query.where(
                or_(
                    User.first_name.contains(user_filter.search),
                    User.last_name.contains(user_filter.search),
                    User.email.contains(user_filter.search),
                    User.mobile_number.contains(user_filter.search),
                    User.fix_number.contains(user_filter.search),
                    User.country_code.contains(user_filter.search),
                )
            )
        
        if  user_filter.user_type is not None:
            statement = statement.where(User.user_type == user_filter.user_type)
            count_query = count_query.where(User.user_type == user_filter.user_type)
        
        if user_filter.country_code is not None:
            statement = statement.where(User.country_code == user_filter.country_code)
            count_query = count_query.where(User.country_code == user_filter.country_code)

        if user_filter.order_by == "created_at":
            if user_filter.asc == "asc":
                statement = statement.order_by(User.created_at)
            else:
                statement = statement.order_by(User.created_at.desc())
        elif user_filter.order_by == "last_login":
            if user_filter.asc == "asc":
                statement = statement.order_by(User.last_login)
            else:
                statement = statement.order_by(User.last_login.desc())
        elif user_filter.order_by == "first_name":
            if user_filter.asc == "asc":
                statement = statement.order_by(User.first_name)
            else:
                statement = statement.order_by(User.first_name.desc())
        elif user_filter.order_by == "last_name":
            if user_filter.asc == "asc":
                statement = statement.order_by(User.last_name)
            else:
                statement = statement.order_by(User.last_name.desc())

        total_count = await self.session.execute(count_query)
        total_count = total_count.scalar_one()

        statement = statement.offset((user_filter.page - 1) * user_filter.page_size).limit(
            user_filter.page_size
        )
        result = await self.session.execute(statement)
        users = result.scalars().all()

        return users, total_count

    async def update_last_login(self, user_id: str):
        statement = select(User).where(User.id == user_id)
        result = await self.session.execute(statement)
        user = result.scalars().one()
        user.last_login = datetime.now(timezone.utc)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
    
    async def update_user_status(self, user_id: str,status : str):
        statement = select(User).where(User.id == user_id)
        result = await self.session.execute(statement)
        user = result.scalars().one()
        user.status = status
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def create(self, user_create_input, password_hash: bool = False):
        # Handle both dict and Pydantic model inputs
        if isinstance(user_create_input, dict):
            user_data = user_create_input.copy()
            # Save the plain password before hashing for email notification
            plain_password = user_data["password"]
            if not password_hash:
                user_data["password"] = pwd_context.hash(user_data["password"])
        else:
            # Pydantic model
            user_data = user_create_input.model_dump()
            # Save the plain password before hashing for email notification
            plain_password = user_data["password"]
            if not password_hash:
                user_data["password"] = pwd_context.hash(user_data["password"])
        
        user = User(**user_data)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        
        notification = SendPasswordNotification(
            email=user_data["email"],
            password=plain_password,  # Use the plain password for email
            lang="en"  # Default to English, could be made configurable
        )
        
        notification.send_notification()
        return user

    async def get_by_id(self, user_id: str):
        statement = select(User).where(User.id == user_id)
        result = await self.session.execute(statement)
        user = result.scalars().first()
        return user

    async def get_full_by_id(self, user_id: str):
        statement = select(User).where(User.id == user_id).options(
                selectinload(User.addresses),
                selectinload(User.school_curriculum),
                selectinload(User.professions_status)
            )

        result = await self.session.execute(statement)
        user = result.scalars().first()
        return user
    async def get_by_email(self, user_email: str):
        statement = select(User).where(User.email == user_email)
        result = await self.session.execute(statement)
        user = result.scalars().first()
        return user
    
    async def get_full_by_email(self, user_email: str):
        statement = select(User).where(User.email == user_email).options(
                selectinload(User.addresses),
                selectinload(User.school_curriculum),
                selectinload(User.professions_status)
            )

        result = await self.session.execute(statement)
        user = result.scalars().first()
        return user
    
    
    async def get_users_by_id_lists(self, user_ids: List[str]):
        statement = select(User).where(
            User.id.in_(user_ids)
        )
        result = await self.session.execute(statement)
        users = result.scalars().all()
        return users

    async def update(self, user_id, user_update_input: UpdateUserInput):
        statement = select(User).where(User.id == user_id)
        result = await self.session.execute(statement)
        user = result.scalars().one()
        
        # Traitement spécial pour le mot de passe - ne le hasher que s'il a été fourni
        update_data = user_update_input.model_dump(exclude_none=True)
        
        for key, value in update_data.items():
            if key == "password" and value is not None and value != "":
                # Hasher le mot de passe seulement s'il a été fourni
                setattr(user, key, pwd_context.hash(value))
            elif key != "password":
                # Pour tous les autres champs, les assigner directement
                setattr(user, key, value)
                
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update_password(self, user_id: str, password: str):
        statement = select(User).where(User.id == user_id)
        result = await self.session.execute(statement)
        user = result.scalars().one()
        user.password = pwd_context.hash(password)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update_profile_image(self, user_id: str, picture: str):
        statement = select(User).where(User.id == user_id)
        result = await self.session.execute(statement)
        user = result.scalars().one()
        user.picture = picture
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user


    async def update_phone_or_email(self, user_id: str, email: str):
        statement = select(User).where(User.id == user_id)
        result = await self.session.execute(statement)
        user = result.scalars().one()

        old_email = user.email
        user.email = email

        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        # Sync Moodle email if mapped
        try:
            if user.moodle_user_id and old_email != email:
                moodle = MoodleService()
                await moodle.update_user_email(user_id=int(user.moodle_user_id), email=email)
        except Exception:
            pass
        return user

    async def update_profile(self, user_id: str, input: UpdateUserProfile):
        statement = select(User).where(User.id == user_id)
        result = await self.session.execute(statement)
        user = result.scalars().one()

        user.first_name = input.first_name
        user.last_name = input.last_name
        user.user_type = input.user_type
        user.status = input.status
        user.country_code = input.country_code
        user.birth_date = input.birth_date
        user.civility = input.civility
        user.mobile_number = input.mobile_number
        user.fix_number = input.fix_number
        user.lang = input.lang
        user.two_factor_enabled = input.two_factor_enabled
        
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
    
    async def update_address(self, user_id: str, input: UpdateAddressInput):
        primary_address_statement = select(Address).where(Address.address_type ==AddressTypeEnum.PRIMARY).where(Address.user_id == user_id)
        primary_address_result = await self.session.execute(primary_address_statement)
        primary_address = primary_address_result.scalars().one_or_none()
        
        if primary_address is None:
            primary_address = Address(
                address_type=AddressTypeEnum.PRIMARY,
                user_id=user_id
            )

        
        primary_address.city = input.primary_address_city
        primary_address.country_code = input.primary_address_country_code
        primary_address.street = input.primary_address_street
        primary_address.postal_code = input.primary_address_postal_code
        primary_address.state = input.primary_address_state

        self.session.add(primary_address)
        
        
        billing_address_statement = select(Address).where(Address.address_type ==AddressTypeEnum.BILLING).where(Address.user_id == user_id)
        billing_address_result = await self.session.execute(billing_address_statement)
        billing_address = billing_address_result.scalars().one_or_none()
        
        if billing_address is None:
            billing_address = Address(
                address_type=AddressTypeEnum.BILLING,
                user_id=user_id
            )

        
        billing_address.city = input.billing_address_city
        billing_address.country_code = input.billing_address_country_code
        billing_address.street = input.billing_address_street
        billing_address.postal_code = input.billing_address_postal_code
        billing_address.state = input.billing_address_state

        self.session.add(billing_address)
        
        await self.session.commit()
        
        return primary_address, billing_address
    
    async def update_profession_status_input(self, user_id: str, input: UpdateProfessionStatusInput):
        
        Profession_status_statement = select(ProfessionStatus).where(ProfessionStatus.user_id == user_id)
        Profession_status_result = await self.session.execute(Profession_status_statement)
        Profession_status = Profession_status_result.scalars().one_or_none()
        
        if Profession_status is None:
            Profession_status = ProfessionStatus(
                user_id=user_id
            )
        
        Profession_status.employer = input.employer
        Profession_status.job_position = input.job_position
        Profession_status.socio_professional_category = input.socio_professional_category
        Profession_status.professional_status = input.professional_status
        Profession_status.professional_experience_in_months = input.professional_experience_in_months

        self.session.add(Profession_status)
        
        await self.session.commit()
        return Profession_status
    
    
    async def update_curriculum(self, user_id: str, input: UpdateCurriculumInput):
        curriculum_statement = select(SchoolCurriculum).where(SchoolCurriculum.user_id == user_id)
        curriculum_result = await self.session.execute(curriculum_statement)
        curriculum = curriculum_result.scalars().one_or_none()
        
        if curriculum is None:
            curriculum = SchoolCurriculum(
                user_id=user_id
            )

        
        curriculum.qualification = input.qualification
        curriculum.last_degree_obtained = input.last_degree_obtained
        curriculum.date_of_last_degree = input.date_of_last_degree


        self.session.add(curriculum)
        
        
        return curriculum
    
    
    
    async def update_device_id(self, user_id: str, input: UpdateDeviceInput):
        statement = select(User).where(User.id == user_id)
        result = await self.session.execute(statement)
        user = result.scalars().one()
        

        user.web_token = input.device_id

        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
    

    async def delete_user(self, user_id: str):
        statement = select(User).where(User.id == user_id)
        result = await self.session.execute(statement)
        user = result.scalars().one()
        user.email = "#" + user.email.replace('@', '#') +"#"
        user.status = UserStatusEnum.DELETED
        user.delete_at = datetime.now(timezone.utc)
        await self.session.commit()
        return user


    async def assign_role(self, user_id: str, role_id: str):
        
        statement = select(UserRole).where(UserRole.user_id == user_id)
        result = await self.session.execute(statement)
        user_roles = result.scalars().all()
        for user_role in user_roles:
            self.session.delete(user_role)
            
        await self.session.commit()
        
        statement = select(UserRole).where(UserRole.user_id == user_id).where(UserRole.role_id == role_id )
        result = await self.session.execute(statement)
        user_role = result.scalars().one_or_none()
        if user_role is not None:    
            return user_role

        user_role = UserRole(user_id=user_id, role_id=role_id)
        self.session.add(user_role)
        await self.session.commit()
        await self.session.refresh(user_role)
        return {"user_id": user_id, "role_id": role_id}
    
    async def revoke_role(self, user_id: str, role_id: int) -> dict:
        """
        Supprime le rôle d'un utilisateur s'il existe.
        Retourne le user_id et role_id dans tous les cas.
        """

        # Cherche le UserRole correspondant
        statement = select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id
        )
        result = await self.session.execute(statement)
        user_role = result.scalars().one_or_none()

        # Si le rôle n'existe pas, on retourne quand même les ids
        if not user_role:
            return {"user_id": user_id, "role_id": role_id, "revoked": False}

        # Supprime le rôle et commit
        await self.session.delete(user_role)
        await self.session.commit()

        return {"user_id": user_id, "role_id": role_id, "revoked": True}
    
    async def assign_permissions(self, user_id: str, permissions: list[str]):
        for permission in permissions:
            statement = select(UserPermission).where(UserPermission.user_id == user_id).where(UserPermission.permission == permission )
            result = await self.session.execute(statement)
            user_permission = result.scalars().one_or_none()
            if user_permission is not None:    
                continue

            user_permission = UserPermission(user_id=user_id, permission=permission)
            self.session.add(user_permission)
            await self.session.commit()
            await self.session.refresh(user_permission)
            
        return {"user_id": user_id, "permission_ids": permissions}

    async def revoke_permissions(self, user_id: str, permissions: list[str]):
        for permission in permissions:
            statement = select(UserPermission).where(UserPermission.user_id == user_id).where(UserPermission.permission == permission )
            result = await self.session.execute(statement)
            user_permission = result.scalars().one_or_none()
            if user_permission is None:    
                continue

            self.session.delete(user_permission)
            await self.session.commit()
        return {"user_id": user_id, "permission_ids": permissions}
    
    async def get_all_user_permissions(self, user_id: str):
        statement = select(UserRole.role_id).where(UserRole.user_id == user_id)
        result = await self.session.execute(statement)
        roles = result.scalars().all()
        
        
        statement = select(UserPermission).where(
            or_(
                UserPermission.user_id == user_id,
                UserPermission.role_id.in_(roles)
                )
        )
        result = await self.session.execute(statement)
        user_permissions = result.scalars().all()
        return user_permissions
    
    async def permission_set_up(self):
        statement = select(User).where(User.email == "admin@lafaom.com")
        result = await self.session.execute(statement)
        user = result.scalars().first()

        if user is None:
            user = User(
                first_name="admin",
                last_name="admin",
                country_code="SN",
                birth_date=date.today(),
                civility= CivilityEnum.MR,
                email="admin@lafaom.com",
                mobile_number="0000000000",
                fix_number="0000000000",
                lang="fr",
                status=UserStatusEnum.ACTIVE,
                password=pwd_context.hash("admin"),
                user_type=UserTypeEnum.ADMIN
            )
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)

        admin = None
        for role in RoleEnum:
            statement = select(Role).where(Role.name == role.value)
            result = await self.session.execute(statement)
            role_data = result.scalars().first()
            if role_data is None:
                role_data = Role(name=role)
                self.session.add(role_data)

            if role_data.name == RoleEnum.SUPER_ADMIN.value:
                admin = role_data

        await self.session.commit()
        await self.session.refresh(admin)

        if admin is not None:
            for permission in PermissionEnum:
                statement = (
                    select(UserPermission).where(UserPermission.role_id == admin.id)
                    .where(UserPermission.permission == permission.value)
                )
                result = await self.session.execute(statement)
                user_permission = result.scalars().first()
                if user_permission is None:
                    user_permission = UserPermission(
                        role_id=admin.id,
                        permission=permission.value
                    )
                    self.session.add(user_permission)

        await self.session.commit()

        statement = select(UserRole).where(UserRole.user_id == user.id).where(UserRole.role_id == admin.id)
        result = await self.session.execute(statement)
        user_role = result.scalars().first()

        if user_role is None:
            user_role = UserRole(
                user_id=user.id,
                role_id=admin.id
            )
            self.session.add(user_role)

            await self.session.commit()

        return True

    async def has_all_permissions(self,user_id :str, permissions : list = []) -> bool: 
        statement = select(UserRole.role_id).where(UserRole.user_id == user_id)
        
        roles_result = await self.session.execute(statement)
        roles = roles_result.scalars().all()
        
        statement = (select(UserPermission).where(UserPermission.user_id == user_id or UserPermission.role_id.in_(roles))
                        .where(UserPermission.permission.in_(permissions)))
        
        
        values_result = await self.session.execute(statement)
        values = values_result.all()
        
        if len(values) == len(permissions) :
            return True
        
        return False 
    
    async def has_any_permissions(self,user_id :str,  permissions : list = []) -> bool: 
        statement = select(UserRole.role_id).where(UserRole.user_id == user_id)
        
        roles_result = await self.session.execute(statement)
        roles = roles_result.scalars().all()
    
    
        
        statement = (select(UserPermission).where(UserPermission.user_id == user_id or UserPermission.role_id.in_(roles))
                        .where(UserPermission.permission.in_(permissions)))
        
        
        values_result = await self.session.execute(statement)
        values = values_result.all()
        
        if len(values)> 1 :
            return True
        
        return False 
    
    async def get_user_role (self,user_id :str):
        statement = select(Role).join(UserRole, Role.id == UserRole.role_id).where(UserRole.user_id == user_id)
        result = await self.session.execute(statement)
        user_role = result.scalars().all()
        return user_role
    
    async def has_all_role(self,user_id :str, role : list = []) -> bool: 
        
        roles = await self.get_user_role(user_id)
        
        for elt in roles :
            if not (elt.name in role) :
                return False
        
        return True
    
    async def has_any_role(self,user_id :str, role : list = []) -> bool: 
        
        roles = await self.get_user_role(user_id)
        
        for elt in roles :
            if elt.name in role :
                return True
        
        return False

    async def get_all_roles(self):
        statement = select(Role)
        result = await self.session.execute(statement)
        roles = result.scalars().all()
        return roles

    async def get_all_permissions(self):
        return [perm.value for perm in PermissionEnum]
    
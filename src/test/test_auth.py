from datetime import datetime , timezone, timedelta
from fastapi import Depends, HTTPException
import pytest
from fastapi.testclient import TestClient
from src.api.auth.models import TempUser
from src.api.auth.router import router
from src.api.auth.schemas import LoginInput, RefreshTokenInput,RegisterInput, ValidateEmailInput, ValidateChangeEmailCode, ChangeAttributeInput, UpdateUserInput, UpdatePasswordInput, UpdateAccountSettingInput, AuthCodeInput, ValidateForgottenPasswordCode
from src.api.auth.utils import create_access_token, get_current_active_user
from src.api.user.models import User
from src.api.auth.service import AuthService
from src.api.user.service import UserService
from src.helper.schemas import BaseOutFail, ErrorMessage
from unittest.mock import MagicMock
from src.api.auth.utils import get_password_hash

@pytest.fixture
def user_service(db):
    service = UserService(session=db)
    
    return service

@pytest.fixture
def token_service(db):
    service = AuthService(session=db)
    
    return service

@pytest.fixture
def token_service(db) :
    return AuthService(db)



def test_login_success(client: TestClient, user_service):
    user_service.create(RegisterInput(
        email="test_login@example.com",
        password= "password",
        first_name="test", 
        last_name="test",
        country_code='cmr'
    ))
    form_data = LoginInput(account="test_login@example.com", password="password")
    response = client.post("/auth/token", data=form_data.model_dump_json())

    assert response.status_code == 200
    assert response.json()["access_token"]["token_type"] == "bearer"

def test_login_failed_incorrect_email(client):
    
    form_data = LoginInput(account="wrong@example.com", password="password")
    response = client.post("/auth/token", data=form_data.model_dump_json())
    assert response.status_code == 401
    assert response.json()["error_code"] == ErrorMessage.INCORRECT_EMAIL_OR_PASSWORD.value

def test_login_failed_incorrect_password(client):
    
    form_data = LoginInput(account="test_login@example.com", password="wrongpassword")
    response = client.post("/auth/token", data=form_data.model_dump_json())
    assert response.status_code == 401
    assert response.json()["error_code"] == ErrorMessage.INCORRECT_EMAIL_OR_PASSWORD.value

def test_login_failed_both_incorrect(client):
    
    form_data = LoginInput(account="wrong@example.com", password="wrongpassword")
    response = client.post("/auth/token", data=form_data.model_dump_json())
    assert response.status_code == 401
    assert response.json()["error_code"] == ErrorMessage.INCORRECT_EMAIL_OR_PASSWORD.value
    
def test_expired_refresh_token(client,user_service,token_service):
    user =user_service.create(RegisterInput(
        email="test_refresh@example.com",
        password= "password",
        first_name="test", 
        last_name="test",
        country_code='cmr'
    ))
    
    refresh_token, token = token_service.generate_refresh_token(user_id=user.id,expires_delta=timedelta(minutes=-1))
    form_data = RefreshTokenInput(refresh_token=token, device_id=refresh_token.id)

    
    response = client.post("/auth/refresh-token", data=form_data.model_dump_json())
    print(response.json())
        
    assert response.status_code == 400
    assert response.json()["error_code"] == ErrorMessage.REFRESH_TOKEN_HAS_EXPIRED.value
    
def test_successful_token_refresh(client,user_service,token_service):
    user = user_service.get_by_email(user_email="test_refresh@example.com")
    
    refresh_token, token = token_service.generate_refresh_token(user_id=user.id)
    form_data = RefreshTokenInput(refresh_token=token, device_id=refresh_token.id)

    response = client.post("/auth/refresh-token", data=form_data.model_dump_json())
    
    assert response.status_code == 200
    assert response.json()["access_token"]["token_type"] == "bearer"
    
def test_invalid_refresh_token(client,token_service,user_service):
    user = user_service.get_by_email(user_email="test_refresh@example.com")
    
    refresh_token, token = token_service.generate_refresh_token(user_id=user.id)
    form_data = RefreshTokenInput(refresh_token="invalid_token", device_id=refresh_token.id)

    response = client.post("/auth/refresh-token", data=form_data.model_dump_json())
        
    assert response.status_code == 401
    assert response.json()["error_code"] == ErrorMessage.REFRESH_TOKEN_NOT_FOUND.value 


def test_register_success(client):

    register_input = RegisterInput(
        email="test_new@example.com",
        password= "password",
        first_name="test", 
        last_name="test",
        country_code='cmr'
    )
    
    response = client.post("/auth/register", json=register_input.model_dump())

    assert response.status_code == 200
    assert response.json()["success"] == True
    
    
def test_register_with_success(client):

    register_input = RegisterInput(
        email="test_new@example.com",
        password= "password",
        first_name="test", 
        last_name="test",
        country_code='cmr'
    )
    
    response = client.post("/auth/register", json=register_input.model_dump())
    

    assert response.status_code == 200
    assert response.json()["success"] == True    

def test_register_existing_email(client):
    
    register_input = RegisterInput(
        email="test_refresh@example.com",
        password= "password",
        first_name="test", 
        last_name="test",
        country_code='cmr'
    )
    
    response = client.post("/auth/register", json=register_input.model_dump())

    assert response.status_code == 400
    assert response.json()["error_code"] == ErrorMessage.EMAIL_ALREADY_TAKEN.value

def test_register_invalid_input(client):

    register_input = {"invalid": "input"}

    response = client.post("/auth/register", json=register_input)
    print(response.json())

    assert response.status_code == 422   
    
    
def test_validate_email_with_email_already_taken(client, token_service):
    token_service.save_temp_user(
        TempUser(
            email="test_refresh@example.com",
            password= "password",
            first_name="test", 
            last_name="test",
            country_code='cmr',
            code="123456",
            end_time=datetime.now(timezone.utc) + timedelta(minutes=3)
        ).model_dump()
    )
    register_input = ValidateEmailInput(email="test_refresh@example.com", code="123456")
    response = client.post("/auth/validate-email", json=register_input.model_dump())
    assert response.status_code == 400
    assert response.json()["error_code"] == ErrorMessage.EMAIL_ALREADY_TAKEN.value

def test_validate_email_with_temp_user_not_found(client, token_service):
    
    register_input = ValidateEmailInput(email="test@example.com", code="123456")
    response = client.post("/auth/validate-email", json=register_input.model_dump())
    assert response.status_code == 400
    assert response.json()["error_code"] == ErrorMessage.EMAIL_NOT_FOUND.value

def test_validate_email_with_temp_user_inactive(client, token_service):
    token_service.save_temp_user(
        TempUser(
            email="test_email1@example.com",
            password= "password",
            first_name="test", 
            last_name="test",
            country_code='cmr',
            code="123456",
            active=False,
            end_time=datetime.now(timezone.utc) + timedelta(minutes=3)
        ).model_dump()
    )
    
    register_input = ValidateEmailInput(email="test_email1@example.com", code="123456")
    response = client.post("/auth/validate-email", json=register_input.model_dump())
    assert response.status_code == 400
    assert response.json()["error_code"] == ErrorMessage.CODE_ALREADY_USED.value

def test_validate_email_with_temp_user_code_expired(client, token_service):
    token_service.save_temp_user(
        TempUser(
            email="test_email2@example.com",
            password= "password",
            first_name="test", 
            last_name="test",
            country_code='cmr',
            code="123456",
            active=True,
            end_time=datetime.now(timezone.utc) - timedelta(minutes=3)
        ).model_dump()
    )
    
    register_input = ValidateEmailInput(email="test_email2@example.com", code="123456")
    response = client.post("/auth/validate-email", json=register_input.model_dump())
    assert response.status_code == 400
    assert response.json()["error_code"] == ErrorMessage.CODE_HAS_EXPIRED.value

def test_validate_email_with_success(client, token_service):
    token_service.save_temp_user(
        TempUser(
            email="test_email3@example.com",
            password= "password",
            first_name="test", 
            last_name="test",
            country_code='cmr',
            code="123456",
            end_time=datetime.now(timezone.utc) + timedelta(minutes=3)
        ).model_dump()
    )
    register_input = ValidateEmailInput(email="test_email3@example.com", code="123456")
    response = client.post("/auth/validate-email", json=register_input.model_dump())
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "user" in response.json()

def test_validate_email_with_missing_required_fields(client):

    register_input =  {"email" : "test_email3"}
    response = client.post("/auth/validate-email", data=register_input)
    assert response.status_code == 422  
    
def test_two_factor_token_success(client, user_service, token_service):
    user = user_service.create(RegisterInput(
        email="test_2fa@example.com",
        password="password",
        first_name="test",
        last_name="test",
        country_code='cmr'
    ))
    
    code = token_service.save_two_factor_code(
        user_id=user.id,
        account="test_2fa@example.com",
        code="123456"
    )
    
    form_data = ValidateChangeEmailCode(
        account="test_2fa@example.com",
        code="123456"
    )
    
    response = client.post("/auth/two-factor-token", data=form_data.model_dump_json())
    assert response.status_code == 200
    assert response.json()["access_token"]["token_type"] == "bearer"

def test_two_factor_token_invalid_code(client, user_service, token_service):
    form_data = ValidateChangeEmailCode(
        account="test_2fa@example.com",
        code="wrong_code"
    )
    
    response = client.post("/auth/two-factor-token", data=form_data.model_dump_json())
    assert response.status_code == 400
    assert response.json()["error_code"] == ErrorMessage.EMAIL_NOT_FOUND.value

def test_password_forgotten_success(client, user_service):
    user_service.create(RegisterInput(
        email="test_forgot@example.com",
        password="password",
        first_name="test",
        last_name="test",
        country_code='cmr'
    ))
    
    form_data = ChangeAttributeInput(
        account="test_forgot@example.com",
        password="password"
    )
    
    response = client.post("/auth/password-forgotten", data=form_data.model_dump_json())
    assert response.status_code == 200
    assert response.json()["success"] == True

def test_password_forgotten_invalid_email(client):
    form_data = ChangeAttributeInput(
        account="invalid@example.com",
        password="password"
    )
    
    response = client.post("/auth/password-forgotten", data=form_data.model_dump_json())
    assert response.status_code == 200
    assert response.json()["success"] == True

def test_validate_forgotten_password_code_success(client, user_service, token_service):
    user = user_service.create(RegisterInput(
        email="test_forgot1@example.com",
        password="password",
        first_name="test",
        last_name="test",
        country_code='cmr'
    ))
    
    
    
    code = token_service.save_forgotten_password_code(
        user_id=user.id,
        account="test_forgot1@example.com",
        code="123456"
    )
    
    form_data = ValidateForgottenPasswordCode(
        account="test_forgot1@example.com",
        code="123456",
        password="new_password"
    )
    
    response = client.post("/auth/validate-password-forgotten-code", data=form_data.model_dump_json())
    
    assert response.status_code == 200
    assert response.json()["access_token"]["token_type"] == "bearer"

def test_change_account_success(client, user_service):
    user = user_service.create(RegisterInput(
        email="test_change@example.com",
        password="password",
        first_name="test",
        last_name="test",
        country_code='cmr'
    ))
    
    access_token = create_access_token(data={"sub": user.id})
    
    form_data = ChangeAttributeInput(
        account="new_email@example.com",
        password="password"
    )
    
    response = client.post(
        "/auth/change-account",
        data=form_data.model_dump_json(),
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    assert response.json()["success"] == True

def test_validate_change_account_code_success(client, user_service, token_service):
    user = user_service.create(RegisterInput(
        email="test_change1@example.com",
        password="password",
        first_name="test",
        last_name="test",
        country_code='cmr'
    ))
    
    access_token = create_access_token(data={"sub": user.id})

    
    code = token_service.save_change_email_code(
        user_id=user.id,
        account="new_email@example.com",
        code="123456"
    )
    
    form_data = ValidateChangeEmailCode(
        account="new_email@example.com",
        code="123456"
    )
    
    response = client.post(
        "/auth/validate-change-account-code",
        data=form_data.model_dump_json(),
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    assert "data" in response.json()

def test_get_me_success(client, user_service):
    user = user_service.create(RegisterInput(
        email="test_me@example.com",
        password="password",
        first_name="test",
        last_name="test",
        country_code='cmr'
    ))
    
    access_token = create_access_token(data={"sub": user.id})
    
    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    assert "data" in response.json()

def test_update_profile_success(client, user_service):
    user = user_service.create(RegisterInput(
        email="test_update@example.com",
        password="password",
        first_name="test",
        last_name="test",
        country_code='cmr'
    ))
    
    access_token = create_access_token(data={"sub": user.id})
    
    form_data = UpdateUserInput(
        first_name="updated",
        last_name="name",
        country_code='cmr'
    )
    
    response = client.post(
        "/auth/update-profile",
        data=form_data.model_dump_json(),
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    assert response.json()["data"]["first_name"] == "updated"

def test_update_password_success(client, user_service):
    user = user_service.create(RegisterInput(
        email="test_password@example.com",
        password="password",
        first_name="test",
        last_name="test",
        country_code='cmr'
    ))
    
    access_token = create_access_token(data={"sub": user.id})
    
    form_data = UpdatePasswordInput(
        password="password",
        new_password="new_password"
    )
    
    response = client.post(
        "/auth/update-password",
        data=form_data.model_dump_json(),
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    assert "data" in response.json()

def test_update_account_setting_success(client, user_service):
    user = user_service.create(RegisterInput(
        email="test_settings@example.com",
        password="password",
        first_name="test",
        last_name="test",
        country_code='cmr'
    ))
    
    access_token = create_access_token(data={"sub": user.id})
    
    form_data = UpdateAccountSettingInput(
        two_factor_enabled=True,
        login_alert=True,
        prefer_notification="email"
    )
    
    response = client.post(
        "/auth/update-account-setting",
        data=form_data.model_dump_json(),
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    assert response.json()["data"]["two_factor_enabled"] == True

def test_code_auth_success(client, user_service, token_service):
    user = user_service.create(RegisterInput(
        email="test_code@example.com",
        password="password",
        first_name="test",
        last_name="test",
        country_code='cmr'
    ))
    
    code = token_service.create_temp_auth_code(
        user_id=user.id,
        expires_delta=timedelta(minutes=30)
    )
    
    form_data = AuthCodeInput(code=code.code)
    
    response = client.post("/auth/code-auth", data=form_data.model_dump_json())
    assert response.status_code == 200
    assert response.json()["access_token"]["token_type"] == "bearer"

def test_code_auth_invalid_code(client):
    form_data = AuthCodeInput(code="invalid_code")
    
    response = client.post("/auth/code-auth", data=form_data.model_dump_json())
    assert response.status_code == 400
    assert response.json()["error_code"] == ErrorMessage.CODE_NOT_EXIST.value
    
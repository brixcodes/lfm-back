#from sqlmodel import select
#from api.user.models import User

import pytest
from src.api.system.service import SystemService
from src.api.system.schemas import SchoolUserInput
from src.api.auth.schemas import RegisterInput
from src.api.user.service import UserService, FreelancerService
from src.api.auth.utils import create_access_token
from src.helper.schemas import ErrorMessage
from src.api.user.schemas import (
    BecomeFreelancerInput, EducationInput, WorkExperienceInput,
    ListDataInput, ToupesuUserInput
)
from src.api.projects.schemas import InvitationInput

# def test_get_user(client : TestClient):
#     response = client.get(
#         "/users/")
#     assert response.status_code == 200, response.text
#     assert isinstance(response.json(), list), "Expected a list of users"

@pytest.fixture
def user_service(db):
    return UserService(session=db)

@pytest.fixture
def freelancer_service(db):
    return FreelancerService(session=db)

@pytest.fixture
def system_service(db):
    return SystemService(session=db)

@pytest.fixture
def test_user(user_service):
    user  = user_service.get_by_email("test_user@example.com")
    if user is None:
        
        user = user_service.create(RegisterInput(
                email="test_user@example.com",
                password="password",
                first_name="test",
                last_name="user",
                country_code='cmr'
        ))
    
    return user

@pytest.fixture
def test_school(system_service):
    school  = system_service.get_school_by_name("test school")
    if school is None:
        
        school  = system_service.create_schools(
        SchoolUserInput(
            name="test school",
            address="test address",
            description="test description"
            
        )
    )
    
    return school


    
@pytest.fixture
def test_freelancer( freelancer_service, test_user):
    
    if test_user.freelancer is not None:
        freelancer = test_user.freelancer
        if freelancer.active == False:
            freelancer = freelancer_service.activate_freelancer(user_id=test_user.id)
        return freelancer
    
    freelancer_input = BecomeFreelancerInput(
        profession="Software Developer",
        summary="Experienced developer",
        pricing=50
    )
    freelancer = freelancer_service.become_freelancer(input=freelancer_input, user_id=test_user.id)
    
    
    return freelancer

def test_read_freelancers(client):
    response = client.get("/freelancers?page=1")
    
    assert response.status_code == 200
    assert "data" in response.json()
    assert "page" in response.json()

def test_become_freelancer_success(client, test_user):
    access_token = create_access_token(data={"sub": test_user.id})
    
    input_data = BecomeFreelancerInput(
        profession="Software Developer",
        summary="Experienced developer",
        pricing=50
    )
    
    response = client.post(
        "/freelancers/become-freelancer",
        json=input_data.model_dump(),
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Request to become freelancer sent successfully"

def test_become_freelancer_already_freelancer(client, test_user, test_freelancer):
    access_token = create_access_token(data={"sub": test_user.id})
    
    input_data = BecomeFreelancerInput(
        profession="Software Developer",
        summary="Experienced developer",
        pricing=50
    )
    
    response = client.post(
        "/freelancers/become-freelancer",
        json=input_data.model_dump(),
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 400
    assert response.json()["error_code"] == ErrorMessage.USER_ALREADY_FREELANCER.value

def test_add_education_success(client, test_user, test_freelancer,test_school):
    access_token = create_access_token(data={"sub": test_user.id})
    

    input_data = EducationInput(
        school_id=test_school.id,
        diploma="Bachelor's Degree",
        field_study="Computer Science",
        start_date="2020-01-01",
        end_date="2024-01-01",
        visibility=1
    )

    
    response = client.post(
        "/freelancers/add-education",
        data=input_data.model_dump_json(),
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 200
    assert "data" in response.json()

def test_update_education_success(client, test_user, test_freelancer, freelancer_service,test_school):
    access_token = create_access_token(data={"sub": test_user.id})
    
    # First add education
    education = freelancer_service.add_education(
        user_id=test_user.id,
        input=EducationInput(
            school_id=test_school.id,
            diploma="Bachelor's",
            field_study="Computer Science",
            start_date="2020-01-01",
            end_date="2024-01-01",
            visibility=1
        )
    )
    
    # Then update it
    input_data = EducationInput(
        school_id=test_school.id,
        diploma="Master's",
        field_study="Computer Science",
        start_date="2020-01-01",
        end_date="2024-01-01",
        visibility=1
    )
    
    response = client.put(
        f"/freelancers/update-education/{education.id}",
        data=input_data.model_dump_json(),
        headers={"Authorization": f"Bearer {access_token}"}
    )
    print(response.json())
    assert response.status_code == 200
    assert response.json()["data"]["diploma"] == "Master's"

def test_delete_education_success(client, test_user, test_freelancer, freelancer_service,test_school):
    access_token = create_access_token(data={"sub": test_user.id})
    
    # First add education
    education = freelancer_service.add_education(
        user_id=test_user.id,
        input=EducationInput(
            school_id=test_school.id,
            diploma="Bachelor's",
            field_study="Computer Science",
            start_date="2020-01-01",
            end_date="2024-01-01",
            visibility=1
        )
    )
    
    response = client.delete(
        f"/freelancers/delete-education/{education.id}",
        headers={"Authorization": f"Bearer {access_token}"}
    )
  
    assert response.status_code == 200
    assert "data" in response.json()

def test_add_work_experience_success(client, test_user, test_freelancer):
    access_token = create_access_token(data={"sub": test_user.id})
    
    input_data = WorkExperienceInput(
        title="Software Engineer",
        company="Tech Corp",
        position="Remote",
        start_date="2020-01-01",
        end_date="2024-01-01",
        description="Full stack development",
        visibility=1
    )
    
    response = client.post(
        "/freelancers/add-work-experience",
        data=input_data.model_dump_json(),
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    assert "data" in response.json()

def test_update_work_experience_success(client, test_user, test_freelancer, freelancer_service):
    access_token = create_access_token(data={"sub": test_user.id})
    
    # First add work experience
    work_exp = freelancer_service.add_work_experience(
        user_id=test_user.id,
        input=WorkExperienceInput(
            title="Software Engineer",
            company="Tech Corp",
            position="Remote",
            start_date="2020-01-01",
            end_date="2024-01-01",
            description="Full stack development",
            visibility=1
        )
    )
    
    # Then update it
    input_data = WorkExperienceInput(
        title="Senior Software Engineer",
        company="Tech Corp",
        position="Remote",
        start_date="2020-01-01",
        end_date="2024-01-01",
        description="Full stack development",
        visibility=1
    )
    
    response = client.put(
        f"/freelancers/update-work-experience/{work_exp.id}",
        data=input_data.model_dump_json(),
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    assert response.json()["data"]["title"] == "Senior Software Engineer"

def test_delete_work_experience_success(client, test_user, test_freelancer, freelancer_service):
    access_token = create_access_token(data={"sub": test_user.id})
    
    # First add work experience
    work_exp = freelancer_service.add_work_experience(
        user_id=test_user.id,
        input=WorkExperienceInput(
            title="Software Engineer",
            company="Tech Corp",
            position="Remote",
            start_date="2020-01-01",
            end_date="2024-01-01",
            description="Full stack development",
            visibility=1
        )
    )
    
    response = client.delete(
        f"/freelancers/delete-work-experience/{work_exp.id}",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    
    assert response.status_code == 200
    assert "data" in response.json()

def test_update_skills_success(client, test_user, test_freelancer):
    access_token = create_access_token(data={"sub": test_user.id})
    
    input_data = ListDataInput(
        data=[1, 2, 3]  # Skill IDs
    )
    
    response = client.post(
        "/freelancers/update-skill",
        json=input_data.model_dump(),
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    assert "data" in response.json()

def test_update_certifications_success(client, test_user, test_freelancer):
    access_token = create_access_token(data={"sub": test_user.id})
    
    input_data = ListDataInput(
        data=[1, 2, 3]  # Certification IDs
    )
    
    response = client.post(
        "/freelancers/update-certification",
        json=input_data.model_dump(),
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    assert "data" in response.json()

def test_update_languages_success(client, test_user, test_freelancer):
    access_token = create_access_token(data={"sub": test_user.id})
    
    input_data = ListDataInput(
        data=[1, 2, 3]  # Language IDs
    )
    
    response = client.post(
        "/freelancers/update-language",
        json=input_data.model_dump(),
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    assert "data" in response.json()

def test_get_favorite_freelancers(client, test_user):
    access_token = create_access_token(data={"sub": test_user.id})
    
    response = client.get(
        "/freelancers/favorite-freelancer",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    assert "data" in response.json()

def test_add_favorite_freelancer_success(client, test_user, user_service):
   
    
    # Create another user who is a freelancer
    other_user = user_service.create(RegisterInput(
        email="other_freelancer@example.com",
        password="password",
        first_name="other",
        last_name="freelancer",
        country_code='cmr'
    ))
    
    access_token = create_access_token(data={"sub": other_user.id})
    
    input_data = InvitationInput(
        user_id=test_user.id
    )
    
    response = client.post(
        "/freelancers/add-favorite-freelancer",
        json=input_data.model_dump(),
        headers={"Authorization": f"Bearer {access_token}"}
    )
    print(response.json())
    assert response.status_code == 200
    assert "data" in response.json()

def test_remove_favorite_freelancer_success(client, test_user, user_service):
    access_token = create_access_token(data={"sub": test_user.id})
    
    # Create another user who is a freelancer
    other_user = user_service.create(RegisterInput(
        email="other_freelancer2@example.com",
        password="password",
        first_name="other",
        last_name="freelancer",
        country_code='cmr'
    ))
    
    # First add as favorite
    user_service.add_favorite(user_id=other_user.id, freelancer_id=test_user.id)
    
    access_token = create_access_token(data={"sub": other_user.id})
    
    input_data = InvitationInput(
        user_id=test_user.id
    )
    
    response = client.post(
        "/freelancers/remove-favorite-freelancer",
        json=input_data.model_dump(),
        headers={"Authorization": f"Bearer {access_token}"}
    )
    print(response.json())
    assert response.status_code == 200
    assert "data" in response.json()

def test_add_toupesu_account_success(client, test_user, test_freelancer):
    access_token = create_access_token(data={"sub": test_user.id})
    
    input_data = ToupesuUserInput(
        toupesu_account="test_account",
        toupesu_username="test_user",
        toupesu_user_id="123"
    )
    
    response = client.post(
        "/users/add-toupesu-cash-out-account",
        json=input_data.model_dump(),
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    assert "data" in response.json()

def test_get_client_dashboard_data(client, test_user):
    access_token = create_access_token(data={"sub": test_user.id})
    
    response = client.get(
        "/stats/get-client-dashboard-data",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    assert "data" in response.json()

def test_get_freelancer_dashboard_data(client, test_user, test_freelancer):
    access_token = create_access_token(data={"sub": test_user.id})
    
    response = client.get(
        "/stats/get-freelancer-dashboard-data",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    assert "data" in response.json()

def test_get_freelancer_revenue_data(client, test_user, test_freelancer):
    access_token = create_access_token(data={"sub": test_user.id})
    
    response = client.get(
        "/stats/get-freelancer-revenue-data",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    assert "data" in response.json()

def test_get_user_by_id_success(client, test_user):
    response = client.get(f"/users/{test_user.id}")
    assert response.status_code == 200
    assert "data" in response.json()

def test_get_user_by_id_not_found(client):
    response = client.get("/users/nonexistent_id")
    assert response.status_code == 400
    assert response.json()["error_code"] == ErrorMessage.USER_NOT_FOUND.value


# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
from django.contrib.auth import get_user_model
from django.test import override_settings
from apps.accounts.models import UserRole

User = get_user_model()


@pytest.mark.django_db
def test_login_success(client):
    user = User.objects.create_user(username='testuser', password='password123', role=UserRole.BUYER)
    response = client.post('/api/v1/auth/login/', {'username': 'testuser', 'password': 'password123'}, content_type='application/json')
    assert response.status_code == 200
    assert response.data['username'] == 'testuser'
    assert 'sessionid' in response.cookies


@pytest.mark.django_db
def test_login_invalid_credentials(client):
    response = client.post('/api/v1/auth/login/', {'username': 'wrong', 'password': 'bad'}, content_type='application/json')
    assert response.status_code == 400
    assert 'error' in response.data


@pytest.mark.django_db
def test_register_buyer(client):
    payload = {
        'username': 'new_buyer_1',
        'email': 'buyer1@test.com',
        'password': 'StrongPassword123!',
        'role': 'BUYER'
    }
    response = client.post('/api/v1/auth/register/', payload, content_type='application/json')
    assert response.status_code == 201
    user = User.objects.get(username='new_buyer_1')
    assert user.role == UserRole.BUYER
    assert user.is_buyer is True


@pytest.mark.django_db
def test_register_agent(client):
    payload = {
        'username': 'new_agent_1',
        'email': 'agent1@test.com',
        'password': 'StrongPassword123!',
        'role': 'AGENT',
        'agency_name': 'Prestige Realty',
        'license_number': 'WB-RERA-2026-9999'
    }
    response = client.post('/api/v1/auth/register/', payload, content_type='application/json')
    assert response.status_code == 201
    user = User.objects.get(username='new_agent_1')
    assert user.role == UserRole.AGENT
    assert user.is_agent is True


@pytest.mark.django_db
def test_demo_login_buyer(client):
    response = client.post('/api/v1/auth/demo-login/', {'persona': 'buyer'}, content_type='application/json')
    assert response.status_code == 200
    assert response.data['user']['username'] == 'buyer_rahul'
    assert response.data['user']['role'] == 'BUYER'
    assert 'sessionid' in response.cookies


@pytest.mark.django_db
def test_demo_login_agent(client):
    response = client.post('/api/v1/auth/demo-login/', {'persona': 'agent'}, content_type='application/json')
    assert response.status_code == 200
    assert response.data['user']['username'] == 'agent_priya'
    assert response.data['user']['role'] == 'AGENT'
    assert 'sessionid' in response.cookies


@pytest.mark.django_db
def test_demo_login_admin(client):
    response = client.post('/api/v1/auth/demo-login/', {'persona': 'admin'}, content_type='application/json')
    assert response.status_code == 200
    assert response.data['user']['username'] == 'admin'
    assert response.data['user']['role'] == 'ADMIN'
    assert 'sessionid' in response.cookies


@pytest.mark.django_db
@override_settings(DEMO_MODE=False)
def test_demo_login_disabled_in_production(client):
    response = client.post('/api/v1/auth/demo-login/', {'persona': 'buyer'}, content_type='application/json')
    assert response.status_code == 403
    assert 'disabled' in response.data['error']

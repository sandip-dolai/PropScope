# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
from django.contrib.auth import get_user_model
# pyrefly: ignore [missing-import]
from django.contrib.gis.geos import Point
from apps.accounts.models import UserRole
from apps.properties.models import Property, PropertyStatus, PropertyType
from apps.favorites.models import Favorite

User = get_user_model()


@pytest.fixture
def buyer_user(db):
    return User.objects.create_user(
        username='buyer_test',
        password='password123',
        role=UserRole.BUYER
    )


@pytest.fixture
def agent_user(db):
    return User.objects.create_user(
        username='agent_test',
        password='password123',
        role=UserRole.AGENT
    )


@pytest.fixture
def sample_property(db, agent_user):
    return Property.objects.create(
        agent=agent_user,
        title="Eco Park Skyline Flat",
        description="Luxury apartment with lake view",
        property_type=PropertyType.APARTMENT,
        status=PropertyStatus.ACTIVE,
        price=8500000.00,
        bedrooms=3,
        bathrooms=2,
        area_sqft=1450.00,
        address="Major Arterial Road, New Town",
        location=Point(88.4600, 22.5900, srid=4326)
    )


@pytest.mark.django_db
def test_favorite_unauthenticated_blocked(client):
    response = client.get('/api/v1/favorites/')
    assert response.status_code in [401, 403]


@pytest.mark.django_db
def test_favorite_lifecycle(client, buyer_user, sample_property):
    # Log in as buyer
    client.force_login(buyer_user)

    # 1. Check initially empty
    resp_empty = client.get('/api/v1/favorites/')
    assert resp_empty.status_code == 200
    assert len(resp_empty.data) == 0

    # 2. Add to favorites
    resp_add = client.post(
        '/api/v1/favorites/',
        {'property_id': sample_property.id},
        content_type='application/json'
    )
    assert resp_add.status_code == 201
    assert resp_add.data['created'] is True
    assert Favorite.objects.filter(user=buyer_user, property=sample_property).exists()

    # 3. Check IDs endpoint
    resp_ids = client.get('/api/v1/favorites/ids/')
    assert resp_ids.status_code == 200
    assert resp_ids.data['favorite_ids'] == [sample_property.id]

    # 4. Check full list contains property
    resp_list = client.get('/api/v1/favorites/')
    assert resp_list.status_code == 200
    assert len(resp_list.data) == 1
    assert resp_list.data[0]['id'] == sample_property.id
    assert resp_list.data[0]['title'] == "Eco Park Skyline Flat"

    # 5. Delete from favorites
    resp_del = client.delete(f'/api/v1/favorites/{sample_property.id}/')
    assert resp_del.status_code == 200
    assert not Favorite.objects.filter(user=buyer_user, property=sample_property).exists()

    # 6. Verify empty again
    resp_ids_empty = client.get('/api/v1/favorites/ids/')
    assert resp_ids_empty.data['favorite_ids'] == []


@pytest.mark.django_db
def test_favorite_duplicate_idempotent(client, buyer_user, sample_property):
    client.force_login(buyer_user)
    client.post('/api/v1/favorites/', {'property_id': sample_property.id}, content_type='application/json')
    resp_dup = client.post('/api/v1/favorites/', {'property_id': sample_property.id}, content_type='application/json')
    assert resp_dup.status_code == 201
    assert resp_dup.data['created'] is False
    assert Favorite.objects.filter(user=buyer_user, property=sample_property).count() == 1


@pytest.mark.django_db
def test_favorite_nonexistent_property(client, buyer_user):
    client.force_login(buyer_user)
    resp = client.post('/api/v1/favorites/', {'property_id': 999999}, content_type='application/json')
    assert resp.status_code == 404
    assert 'error' in resp.data

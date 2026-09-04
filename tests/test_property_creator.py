# pyrefly: ignore [missing-import]
import pytest
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point, Polygon, MultiPolygon
from apps.accounts.models import UserRole
from apps.properties.models import Property, PropertyStatus, PropertyType
from apps.amenities.models import Amenity, AmenityCategory
from apps.geography.models import Area

User = get_user_model()


@pytest.fixture
def agent_user(db):
    return User.objects.create_user(
        username='agent_creator',
        password='password123',
        role=UserRole.AGENT
    )


@pytest.fixture
def buyer_user(db):
    return User.objects.create_user(
        username='buyer_intruder',
        password='password123',
        role=UserRole.BUYER
    )


@pytest.fixture
def sample_amenity(db):
    category = AmenityCategory.objects.create(name='Metro Station', icon='train')
    return Amenity.objects.create(
        name='Salt Lake Sector V Metro',
        category=category,
        location=Point(88.4320, 22.5860, srid=4326),
        address='Sector V, Salt Lake'
    )


@pytest.fixture
def sample_area(db):
    poly = Polygon(((88.40, 22.56), (88.45, 22.56), (88.45, 22.60), (88.40, 22.60), (88.40, 22.56)))
    return Area.objects.create(
        name='Salt Lake (Bidhannagar)',
        city='Kolkata',
        boundary=MultiPolygon(poly)
    )


@pytest.mark.django_db
def test_amenity_nearest_point_api(client, sample_amenity, sample_area):
    resp = client.get('/api/v1/amenities/nearest/?lat=22.5850&lng=88.4300')
    assert resp.status_code == 200
    data = resp.data
    assert 'nearest_amenities' in data
    assert len(data['nearest_amenities']) >= 1
    assert data['nearest_amenities'][0]['amenity_name'] == 'Salt Lake Sector V Metro'
    assert 'distance_km' in data['nearest_amenities'][0]
    assert 'proximity_score' in data['nearest_amenities'][0]
    assert 'proximity_label' in data['nearest_amenities'][0]

    # Check detected submarket
    assert data['submarket'] is not None
    assert data['submarket']['name'] == 'Salt Lake (Bidhannagar)'


@pytest.mark.django_db
def test_amenity_nearest_point_invalid_coords(client):
    resp = client.get('/api/v1/amenities/nearest/?lat=invalid&lng=abc')
    assert resp.status_code == 400


@pytest.mark.django_db
def test_property_creation_by_agent(client, agent_user):
    client.force_login(agent_user)
    payload = {
        "title": "New Town Eco Park Villa",
        "description": "Exclusive spatial listing with panoramic park views",
        "property_type": "VILLA",
        "status": "ACTIVE",
        "price": 17500000.00,  # 1.75 Cr
        "bedrooms": 4,
        "bathrooms": 3.5,
        "area_sqft": 2800.00,
        "address": "Street 104, Action Area I, New Town",
        "latitude": 22.5920,
        "longitude": 88.4650
    }

    resp = client.post('/api/v1/properties/', payload, content_type='application/json')
    assert resp.status_code == 201

    prop_id = resp.data['id']
    prop = Property.objects.get(id=prop_id)
    assert prop.title == "New Town Eco Park Villa"
    assert prop.agent == agent_user
    assert prop.price == 17500000.00
    assert prop.price_per_sqft == 6250.00  # 17,500,000 / 2,800
    assert prop.location.x == 88.4650
    assert prop.location.y == 22.5920


@pytest.mark.django_db
def test_property_creation_unauthenticated_blocked(client):
    resp = client.post('/api/v1/properties/', {'title': 'Blocked'}, content_type='application/json')
    assert resp.status_code in [401, 403]


@pytest.mark.django_db
def test_property_creation_buyer_blocked(client, buyer_user):
    client.force_login(buyer_user)
    payload = {
        "title": "Illegal Buyer Property",
        "description": "Should be rejected",
        "property_type": "APARTMENT",
        "status": "ACTIVE",
        "price": 5000000.00,
        "bedrooms": 2,
        "bathrooms": 2.0,
        "area_sqft": 1000.00,
        "address": "Anywhere",
        "latitude": 22.58,
        "longitude": 88.43
    }
    resp = client.post('/api/v1/properties/', payload, content_type='application/json')
    assert resp.status_code == 403


@pytest.mark.django_db
def test_property_create_page_rendered_for_agent(client, agent_user):
    client.force_login(agent_user)
    resp = client.get('/dashboard/create/')
    assert resp.status_code == 200
    content = resp.content.decode('utf-8')
    assert "Spatial Asset Induction" in content
    assert "pinDropMap" in content
    assert "Publish Geospatial Listing" in content

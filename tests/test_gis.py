import pytest
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from rest_framework.test import APIClient
from apps.accounts.models import UserRole
from apps.properties.models import Property, PropertyStatus, PropertyType

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def agent_user():
    return User.objects.create_user(
        username='gis_agent',
        password='password123',
        role=UserRole.AGENT
    )


@pytest.fixture
def sample_properties(agent_user):
    # Property 1: Salt Lake Sector V (22.5840, 88.4250)
    p1 = Property.objects.create(
        agent=agent_user,
        title="Sector V Tech Flat",
        description="Close to IT hub",
        property_type=PropertyType.APARTMENT,
        status=PropertyStatus.ACTIVE,
        price=7500000.00,
        bedrooms=3,
        bathrooms=2,
        area_sqft=1400.00,
        address="Sector V, Salt Lake",
        location=Point(88.4250, 22.5840, srid=4326)
    )

    # Property 2: Karunamoyee (22.5860, 88.4210) ~0.5km away
    p2 = Property.objects.create(
        agent=agent_user,
        title="Karunamoyee 2BHK",
        description="Near Central Park",
        property_type=PropertyType.APARTMENT,
        status=PropertyStatus.ACTIVE,
        price=5000000.00,
        bedrooms=2,
        bathrooms=2,
        area_sqft=950.00,
        address="Karunamoyee, Salt Lake",
        location=Point(88.4210, 22.5860, srid=4326)
    )

    # Property 3: Distant Villa (22.7000, 88.5500) ~20km away
    p3 = Property.objects.create(
        agent=agent_user,
        title="Distant Suburb Villa",
        description="Far away villa",
        property_type=PropertyType.VILLA,
        status=PropertyStatus.ACTIVE,
        price=18000000.00,
        bedrooms=4,
        bathrooms=4,
        area_sqft=3000.00,
        address="Distant Suburb",
        location=Point(88.5500, 22.7000, srid=4326)
    )

    return p1, p2, p3


@pytest.mark.django_db
def test_api_radius_search(api_client, sample_properties):
    p1, p2, p3 = sample_properties

    # Radius 2km from Sector V (22.5840, 88.4250)
    url = "/api/v1/properties/radius-search/?lat=22.5840&lng=88.4250&radius_km=2"
    response = api_client.get(url)

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    returned_ids = [item["id"] for item in data["results"]]
    assert p1.id in returned_ids
    assert p2.id in returned_ids
    assert p3.id not in returned_ids


@pytest.mark.django_db
def test_api_bbox_search(api_client, sample_properties):
    p1, p2, p3 = sample_properties

    # Viewport Bounding box covering Salt Lake (minLng,minLat,maxLng,maxLat)
    url = "/api/v1/properties/bbox-search/?bbox=88.410,22.570,88.440,22.600"
    response = api_client.get(url)

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    returned_ids = [item["id"] for item in data["results"]]
    assert p1.id in returned_ids
    assert p2.id in returned_ids
    assert p3.id not in returned_ids


@pytest.mark.django_db
def test_api_polygon_search(api_client, sample_properties):
    p1, p2, p3 = sample_properties

    # Polygon enclosing Salt Lake
    payload = {
        "geojson": {
            "type": "Polygon",
            "coordinates": [
                [
                    [88.410, 22.570],
                    [88.440, 22.570],
                    [88.440, 22.600],
                    [88.410, 22.600],
                    [88.410, 22.570]
                ]
            ]
        }
    }
    response = api_client.post("/api/v1/properties/polygon-search/", payload, format='json')

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    returned_ids = [item["id"] for item in data["results"]]
    assert p1.id in returned_ids
    assert p2.id in returned_ids
    assert p3.id not in returned_ids

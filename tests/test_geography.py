import pytest
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point, Polygon, MultiPolygon
from rest_framework.test import APIClient
from apps.accounts.models import UserRole
from apps.geography.models import Area
from apps.properties.models import Property, PropertyStatus, PropertyType

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def sample_area_data():
    agent = User.objects.create_user(username='geo_agent', password='password123', role=UserRole.AGENT)

    # MultiPolygon enclosing (88.40, 22.50) to (88.50, 22.60)
    poly = Polygon([
        (88.40, 22.50),
        (88.50, 22.50),
        (88.50, 22.60),
        (88.40, 22.60),
        (88.40, 22.50)
    ], srid=4326)
    multi_poly = MultiPolygon([poly], srid=4326)

    area = Area.objects.create(
        name="Test Enclave",
        city="Kolkata",
        description="Test neighborhood boundary",
        boundary=multi_poly
    )

    # Property 1: Inside the polygon (88.45, 22.55)
    prop_in = Property.objects.create(
        agent=agent,
        title="Inside Enclave 3BHK",
        description="Inside property",
        property_type=PropertyType.APARTMENT,
        status=PropertyStatus.ACTIVE,
        price=7000000.00,
        bedrooms=3,
        bathrooms=2,
        area_sqft=1200.00,
        address="Inside address",
        location=Point(88.45, 22.55, srid=4326)
    )

    # Property 2: Outside the polygon (88.30, 22.40)
    prop_out = Property.objects.create(
        agent=agent,
        title="Outside 2BHK",
        description="Outside property",
        property_type=PropertyType.APARTMENT,
        status=PropertyStatus.ACTIVE,
        price=4000000.00,
        bedrooms=2,
        bathrooms=1,
        area_sqft=800.00,
        address="Outside address",
        location=Point(88.30, 22.40, srid=4326)
    )

    return area, prop_in, prop_out


@pytest.mark.django_db
def test_area_list_api(api_client, sample_area_data):
    area, prop_in, prop_out = sample_area_data

    response = api_client.get("/api/v1/areas/")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 1

    area_item = next(a for a in data["results"] if a["id"] == area.id)
    assert area_item["name"] == "Test Enclave"
    assert area_item["property_count"] == 1
    assert area_item["boundary_geojson"]["type"] == "MultiPolygon"


@pytest.mark.django_db
def test_area_properties_containment_api(api_client, sample_area_data):
    area, prop_in, prop_out = sample_area_data

    response = api_client.get(f"/api/v1/areas/{area.id}/properties/")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["results"][0]["id"] == prop_in.id
    assert data["results"][0]["title"] == "Inside Enclave 3BHK"


@pytest.mark.django_db
def test_area_not_found(api_client):
    response = api_client.get("/api/v1/areas/99999/properties/")
    assert response.status_code == 404

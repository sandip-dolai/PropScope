import pytest
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from rest_framework.test import APIClient
from apps.accounts.models import UserRole
from apps.properties.models import Property, PropertyStatus, PropertyType
from apps.amenities.models import Amenity, AmenityCategory
from apps.amenities.services import AmenitySpatialService

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def agent_user():
    return User.objects.create_user(
        username='amenity_agent',
        password='password123',
        role=UserRole.AGENT
    )


@pytest.fixture
def sample_data(agent_user):
    metro_cat = AmenityCategory.objects.create(name="Metro Station", icon="train")
    hospital_cat = AmenityCategory.objects.create(name="Hospital", icon="cross")

    # Metro A: 500m away (22.5850, 88.4250)
    metro_close = Amenity.objects.create(
        category=metro_cat,
        name="Close Metro",
        location=Point(88.4250, 22.5850, srid=4326)
    )

    # Metro B: 5km away (22.6300, 88.4250)
    metro_far = Amenity.objects.create(
        category=metro_cat,
        name="Far Metro",
        location=Point(88.4250, 22.6300, srid=4326)
    )

    # Hospital: 1km away (22.5900, 88.4200)
    hospital = Amenity.objects.create(
        category=hospital_cat,
        name="City Care Hospital",
        location=Point(88.4200, 22.5900, srid=4326)
    )

    # Property at (22.5800, 88.4250)
    prop = Property.objects.create(
        agent=agent_user,
        title="Test Skyline Flat",
        description="Near close metro",
        property_type=PropertyType.APARTMENT,
        status=PropertyStatus.ACTIVE,
        price=6000000.00,
        bedrooms=2,
        bathrooms=2,
        area_sqft=1000.00,
        address="Test Address",
        location=Point(88.4250, 22.5800, srid=4326)
    )

    return prop, metro_close, metro_far, hospital


@pytest.mark.django_db
def test_amenity_spatial_service_knn(sample_data):
    prop, metro_close, metro_far, hospital = sample_data

    result = AmenitySpatialService.get_nearest_amenities_for_property(prop)

    assert result["property_id"] == prop.id
    nearest = result["nearest_amenities"]
    assert len(nearest) == 2

    # Find metro category result
    metro_res = next(item for item in nearest if item["category_name"] == "Metro Station")
    assert metro_res["amenity_id"] == metro_close.id
    assert metro_res["distance_km"] < 1.0

    # Find hospital category result
    hosp_res = next(item for item in nearest if item["category_name"] == "Hospital")
    assert hosp_res["amenity_id"] == hospital.id


@pytest.mark.django_db
def test_nearest_amenities_api_endpoint(api_client, sample_data):
    prop, metro_close, metro_far, hospital = sample_data

    url = f"/api/v1/properties/{prop.id}/nearest-amenities/"
    response = api_client.get(url)

    assert response.status_code == 200
    data = response.json()
    assert data["property_id"] == prop.id
    assert len(data["nearest_amenities"]) == 2
    
    # Check proximity scoring fields in response
    metro_item = next(i for i in data["nearest_amenities"] if i["category_name"] == "Metro Station")
    assert metro_item["proximity_score"] == 100.0
    assert "Excellent" in metro_item["proximity_label"]


@pytest.mark.django_db
def test_nearest_amenities_not_found(api_client):
    url = "/api/v1/properties/99999/nearest-amenities/"
    response = api_client.get(url)
    assert response.status_code == 404


def test_amenity_proximity_scorer_thresholds():
    from apps.amenities.scoring import AmenityProximityScorer

    scorer = AmenityProximityScorer()

    # Metro thresholds: <1km=100, <2.5km=75, <5km=45, >5km=20
    score, label = scorer.score_category("Metro Station", 0.6)
    assert score == 100.0
    assert "Excellent" in label

    score, label = scorer.score_category("Metro Station", 1.8)
    assert score == 75.0
    assert "Good" in label

    score, label = scorer.score_category("Metro Station", 3.2)
    assert score == 45.0
    assert "Moderate" in label

    score, label = scorer.score_category("Metro Station", 6.0)
    assert score == 20.0
    assert "Poor" in label


def test_enrich_nearest_amenities():
    from apps.amenities.scoring import AmenityProximityScorer

    scorer = AmenityProximityScorer()
    sample_list = [
        {"category_name": "Hospital", "distance_km": 1.2, "amenity_name": "Apollo"},
        {"category_name": "Park", "distance_km": 4.5, "amenity_name": "Eco Park"},
    ]

    enriched = scorer.enrich_nearest_amenities(sample_list)
    assert len(enriched) == 2
    assert enriched[0]["proximity_score"] == 100.0
    assert enriched[0]["proximity_label"] == "Immediate (<1.5 km)"
    assert enriched[1]["proximity_score"] == 25.0


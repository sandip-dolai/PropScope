import pytest
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from rest_framework.test import APIClient
from apps.accounts.models import UserRole
from apps.properties.models import Property, PropertyStatus, PropertyType
from apps.amenities.models import Amenity, AmenityCategory
from apps.amenities.scoring import (
    DeterministicLocationScoreCalculator,
    DEFAULT_LOCATION_WEIGHTS,
    PILLAR_TRANSPORT,
    PILLAR_HEALTHCARE,
    PILLAR_EDUCATION,
    PILLAR_SHOPPING,
    PILLAR_RECREATION,
)
from apps.amenities.services import AmenitySpatialService
from apps.recommendations.strategies import RuleBasedRecommendation

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def agent_user():
    return User.objects.create_user(
        username='scoring_agent',
        password='password123',
        role=UserRole.AGENT
    )


@pytest.fixture
def full_amenity_setup(agent_user):
    # Setup categories for all 5 pillars
    cat_metro = AmenityCategory.objects.create(name="Metro Station", icon="train")
    cat_hosp = AmenityCategory.objects.create(name="Hospital", icon="cross")
    cat_school = AmenityCategory.objects.create(name="School", icon="school")
    cat_mall = AmenityCategory.objects.create(name="Shopping Mall", icon="shopping-bag")
    cat_park = AmenityCategory.objects.create(name="Park", icon="trees")

    # Property at Sector V (22.5800, 88.4300)
    prop = Property.objects.create(
        agent=agent_user,
        title="Salt Lake Tech Heights",
        description="Premium connected condominium",
        property_type=PropertyType.APARTMENT,
        status=PropertyStatus.ACTIVE,
        price=8500000.00,
        bedrooms=3,
        bathrooms=2,
        area_sqft=1400.00,
        address="Sector V, Salt Lake, Kolkata",
        location=Point(88.4300, 22.5800, srid=4326)
    )

    # 1. Metro: 400m away (<=1.0 km -> 100 score)
    metro = Amenity.objects.create(
        category=cat_metro,
        name="Sector V Metro Station",
        location=Point(88.4310, 22.5830, srid=4326)
    )

    # 2. Hospital: 1.2km away (<=1.5 km -> 100 score)
    hosp = Amenity.objects.create(
        category=cat_hosp,
        name="Apollo Clinic Salt Lake",
        location=Point(88.4200, 22.5820, srid=4326)
    )

    # 3. School: 1.8km away (<=2.0 km -> 100 score)
    school = Amenity.objects.create(
        category=cat_school,
        name="Salt Lake Point School",
        location=Point(88.4180, 22.5750, srid=4326)
    )

    # 4. Mall: 1.5km away (<=2.0 km -> 100 score)
    mall = Amenity.objects.create(
        category=cat_mall,
        name="City Centre 1 Mall",
        location=Point(88.4190, 22.5880, srid=4326)
    )

    # 5. Park: 600m away (<=1.0 km -> 100 score)
    park = Amenity.objects.create(
        category=cat_park,
        name="Central Park Green",
        location=Point(88.4280, 22.5850, srid=4326)
    )

    return prop, metro, hosp, school, mall, park


# ==============================================================================
# 1. Pure Unit Tests: Deterministic Calculator Math & Weight Logic
# ==============================================================================

def test_calculator_default_weights():
    calc = DeterministicLocationScoreCalculator()
    weights = calc.default_weights
    assert weights[PILLAR_TRANSPORT] == 0.30
    assert weights[PILLAR_HEALTHCARE] == 0.20
    assert weights[PILLAR_EDUCATION] == 0.20
    assert weights[PILLAR_SHOPPING] == 0.15
    assert weights[PILLAR_RECREATION] == 0.15
    assert sum(weights.values()) == 1.0


def test_calculator_weight_normalization():
    calc = DeterministicLocationScoreCalculator()
    custom = {
        "transport": 2.0,
        "healthcare": 1.0,
        "education": 1.0,
        "shopping": 0.5,
        "recreation": 0.5,
    }
    normalized = calc.normalize_weights(custom)
    assert normalized[PILLAR_TRANSPORT] == 0.40
    assert normalized[PILLAR_HEALTHCARE] == 0.20
    assert normalized[PILLAR_EDUCATION] == 0.20
    assert normalized[PILLAR_SHOPPING] == 0.10
    assert normalized[PILLAR_RECREATION] == 0.10
    assert round(sum(normalized.values()), 4) == 1.0


def test_calculator_rating_tiers():
    calc = DeterministicLocationScoreCalculator()
    assert calc.get_rating_tier(95.0) == "Prime Location"
    assert calc.get_rating_tier(85.0) == "Prime Location"
    assert calc.get_rating_tier(75.0) == "High Accessibility"
    assert calc.get_rating_tier(60.0) == "Well Connected"
    assert calc.get_rating_tier(45.0) == "Moderate Accessibility"
    assert calc.get_rating_tier(30.0) == "Emerging Suburban"


def test_calculator_deterministic_scoring():
    calc = DeterministicLocationScoreCalculator()
    mock_amenities = [
        {"category_name": "Metro Station", "amenity_name": "Metro A", "distance_km": 0.5, "proximity_score": 100.0, "proximity_label": "Excellent (<1 km)"},
        {"category_name": "Hospital", "amenity_name": "Hospital B", "distance_km": 2.0, "proximity_score": 75.0, "proximity_label": "Accessible (<3.5 km)"},
        {"category_name": "School", "amenity_name": "School C", "distance_km": 3.0, "proximity_score": 70.0, "proximity_label": "Close (<4 km)"},
        {"category_name": "Shopping Mall", "amenity_name": "Mall D", "distance_km": 1.2, "proximity_score": 100.0, "proximity_label": "Very close (<2 km)"},
        {"category_name": "Park", "amenity_name": "Park E", "distance_km": 0.8, "proximity_score": 100.0, "proximity_label": "Within reach (<1 km)"},
    ]
    result = calc.calculate(mock_amenities)

    # Expected:
    # Transport: 100.0 * 0.30 = 30.0
    # Healthcare: 75.0 * 0.20 = 15.0
    # Education: 70.0 * 0.20 = 14.0
    # Shopping: 100.0 * 0.15 = 15.0
    # Recreation: 100.0 * 0.15 = 15.0
    # Total = 30.0 + 15.0 + 14.0 + 15.0 + 15.0 = 89.0
    assert result["composite_score"] == 89.0
    assert result["rating"] == "Prime Location"
    assert len(result["breakdown"]) == 5
    assert result["breakdown"][PILLAR_TRANSPORT]["score"] == 100.0
    assert result["breakdown"][PILLAR_HEALTHCARE]["score"] == 75.0


def test_calculator_missing_amenity_fallback():
    calc = DeterministicLocationScoreCalculator()
    # Only Metro present, other 4 pillars missing
    mock_amenities = [
        {"category_name": "Metro Station", "amenity_name": "Metro Only", "distance_km": 0.4, "proximity_score": 100.0, "proximity_label": "Excellent (<1 km)"},
    ]
    result = calc.calculate(mock_amenities)

    # Transport: 100 * 0.30 = 30.0
    # Other 4 pillars fallback to 20.0:
    # 20 * 0.20 = 4.0
    # 20 * 0.20 = 4.0
    # 20 * 0.15 = 3.0
    # 20 * 0.15 = 3.0
    # Total = 30.0 + 4.0 + 4.0 + 3.0 + 3.0 = 44.0
    assert result["composite_score"] == 44.0
    assert result["rating"] == "Moderate Accessibility"
    assert result["breakdown"][PILLAR_HEALTHCARE]["score"] == 20.0
    assert result["breakdown"][PILLAR_HEALTHCARE]["amenity_name"] == "None within range"


# ==============================================================================
# 2. Integration Tests: AmenitySpatialService & PostGIS KNN
# ==============================================================================

@pytest.mark.django_db
def test_spatial_service_calculate_score(full_amenity_setup):
    prop, metro, hosp, school, mall, park = full_amenity_setup

    score_data = AmenitySpatialService.calculate_location_score_for_property(prop)

    assert score_data["property_id"] == prop.id
    assert score_data["property_title"] == prop.title
    assert "composite_score" in score_data
    assert score_data["composite_score"] >= 80.0
    assert score_data["rating"] in ["Prime Location", "High Accessibility"]

    breakdown = score_data["breakdown"]
    assert PILLAR_TRANSPORT in breakdown
    assert PILLAR_HEALTHCARE in breakdown
    assert PILLAR_EDUCATION in breakdown
    assert PILLAR_SHOPPING in breakdown
    assert PILLAR_RECREATION in breakdown


@pytest.mark.django_db
def test_nearest_amenities_includes_location_score(full_amenity_setup):
    prop, _, _, _, _, _ = full_amenity_setup

    result = AmenitySpatialService.get_nearest_amenities_for_property(prop)
    assert "location_score" in result
    assert result["location_score"]["composite_score"] > 0
    assert "breakdown" in result["location_score"]


# ==============================================================================
# 3. API Endpoint Tests: /api/v1/properties/<id>/location-score/
# ==============================================================================

@pytest.mark.django_db
def test_api_location_score_endpoint(api_client, full_amenity_setup):
    prop, _, _, _, _, _ = full_amenity_setup

    url = f"/api/v1/properties/{prop.id}/location-score/"
    response = api_client.get(url)

    assert response.status_code == 200
    data = response.json()
    assert data["property_id"] == prop.id
    assert "composite_score" in data
    assert "rating" in data
    assert "breakdown" in data
    assert "weights" in data


@pytest.mark.django_db
def test_api_location_score_custom_weights(api_client, full_amenity_setup):
    prop, _, _, _, _, _ = full_amenity_setup

    # Test weight override: 100% transport
    url = f"/api/v1/properties/{prop.id}/location-score/?transport=1.0&healthcare=0&education=0&shopping=0&recreation=0"
    response = api_client.get(url)

    assert response.status_code == 200
    data = response.json()
    assert data["weights"][PILLAR_TRANSPORT] == 1.0
    assert data["composite_score"] == 100.0


@pytest.mark.django_db
def test_api_location_score_not_found(api_client):
    url = "/api/v1/properties/999999/location-score/"
    response = api_client.get(url)
    assert response.status_code == 404


# ==============================================================================
# 4. Recommendation Engine Integration Test
# ==============================================================================

@pytest.mark.django_db
def test_recommendation_strategy_integrates_location_score(full_amenity_setup):
    prop, _, _, _, _, _ = full_amenity_setup

    strategy = RuleBasedRecommendation()
    candidates = Property.objects.filter(id=prop.id)
    preferences = {"max_price": 10000000, "bedrooms": 3}

    results = strategy.recommend(candidates, preferences)
    assert len(results) == 1
    item = results[0]
    assert "location_score" in item
    assert "location_rating" in item
    assert item["location_score"] >= 80.0
    # Verify reason codes mention location score
    assert any("Location score:" in reason for reason in item["reasons"])

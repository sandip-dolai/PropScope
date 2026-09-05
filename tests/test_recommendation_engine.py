import pytest
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point, Polygon, MultiPolygon
from rest_framework.test import APIClient
from apps.accounts.models import UserRole
from apps.properties.models import Property, PropertyStatus, PropertyType
from apps.geography.models import Area
from apps.recommendations.strategies import (
    RuleBasedRecommendation,
    score_budget_fit,
    score_bedroom_fit,
    score_area_fit,
    normalize_dimension_weights,
    DIMENSION_BUDGET,
    DIMENSION_BEDROOM,
    DIMENSION_AREA,
    DIMENSION_LOCATION,
)

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def agent_user():
    return User.objects.create_user(
        username='rec_test_agent',
        password='password123',
        role=UserRole.AGENT
    )


@pytest.fixture
def properties_setup(agent_user):
    # Create an Area boundary in Salt Lake
    poly = Polygon(((88.40, 22.56), (88.44, 22.56), (88.44, 22.60), (88.40, 22.60), (88.40, 22.56)))
    area_salt_lake = Area.objects.create(
        name="Salt Lake Submarket",
        boundary=MultiPolygon([poly])
    )

    # Property 1: Budget-friendly 3BHK inside Salt Lake
    prop1 = Property.objects.create(
        agent=agent_user,
        title="Salt Lake Modern 3BHK",
        property_type=PropertyType.APARTMENT,
        status=PropertyStatus.ACTIVE,
        price=7500000.00,  # 75L
        bedrooms=3,
        bathrooms=2,
        area_sqft=1450.00,
        address="Sector 2, Salt Lake",
        location=Point(88.4200, 22.5800, srid=4326)
    )

    # Property 2: Luxury 4BHK Villa inside Salt Lake
    prop2 = Property.objects.create(
        agent=agent_user,
        title="Salt Lake Luxury Villa",
        property_type=PropertyType.VILLA,
        status=PropertyStatus.ACTIVE,
        price=16000000.00,  # 1.6 Cr
        bedrooms=4,
        bathrooms=4,
        area_sqft=2800.00,
        address="Sector 3, Salt Lake",
        location=Point(88.4250, 22.5850, srid=4326)
    )

    # Property 3: Compact 2BHK outside Salt Lake
    prop3 = Property.objects.create(
        agent=agent_user,
        title="Suburban Starter 2BHK",
        property_type=PropertyType.APARTMENT,
        status=PropertyStatus.ACTIVE,
        price=4500000.00,  # 45L
        bedrooms=2,
        bathrooms=2,
        area_sqft=900.00,
        address="Barasat Highway",
        location=Point(88.5000, 22.7000, srid=4326)
    )

    return prop1, prop2, prop3, area_salt_lake


# ==============================================================================
# 1. Unit Tests: Pure Math Functions
# ==============================================================================

def test_score_budget_fit_under_ceiling():
    # Price 70L, Max budget 80L -> 100 - (70/80)*20 = 82.5
    score = score_budget_fit(price=7000000, max_budget=8000000)
    assert score == 82.5


def test_score_budget_fit_over_ceiling():
    # Price 90L, Max budget 80L -> Over by 10L (12.5% over)
    score = score_budget_fit(price=9000000, max_budget=8000000)
    assert score < 80.0
    assert score > 0.0


def test_score_budget_fit_target_and_max():
    # Target 60L, Max 80L, Price 55L (below target -> 90-100)
    score = score_budget_fit(price=5500000, max_budget=8000000, target_budget=6000000)
    assert score >= 90.0


def test_score_bedroom_fit():
    assert score_bedroom_fit(actual_bhk=3, desired_bhk=3) == 100.0
    assert score_bedroom_fit(actual_bhk=4, desired_bhk=3) == 85.0
    assert score_bedroom_fit(actual_bhk=2, desired_bhk=3) == 60.0
    assert score_bedroom_fit(actual_bhk=1, desired_bhk=3) < 50.0


def test_score_area_fit():
    assert score_area_fit(actual_sqft=1500, target_sqft=1400) >= 90.0
    assert score_area_fit(actual_sqft=1000, target_sqft=1500) < 80.0
    assert score_area_fit(actual_sqft=1200, min_sqft=1000) == 100.0


def test_normalize_dimension_weights():
    custom = {"budget": 2.0, "bedroom": 1.0, "area": 0.5, "location": 0.5}
    norm = normalize_dimension_weights(custom)
    assert norm[DIMENSION_BUDGET] == 0.5
    assert norm[DIMENSION_BEDROOM] == 0.25
    assert norm[DIMENSION_AREA] == 0.125
    assert norm[DIMENSION_LOCATION] == 0.125
    assert sum(norm.values()) == 1.0


# ==============================================================================
# 2. Strategy Tests: RuleBasedRecommendation Ranking & Dimension Scores
# ==============================================================================

@pytest.mark.django_db
def test_rule_based_recommendation_ranking(properties_setup):
    prop1, prop2, prop3, _ = properties_setup
    strategy = RuleBasedRecommendation()

    # Preferences: 3BHK with budget 80L
    preferences = {
        "max_price": 8000000,
        "bedrooms": 3,
        "target_area_sqft": 1400,
    }

    results = strategy.recommend([prop1, prop2, prop3], preferences)

    # prop1 (75L, 3BHK, 1450 sqft) is the ideal match and should rank #1
    assert len(results) == 3
    assert results[0]["property_id"] == prop1.id
    assert results[0]["score"] > results[1]["score"]
    assert results[0]["bedrooms"] == 3
    assert results[0]["bedroom_score"] == 100.0
    assert results[0]["budget_score"] > 80.0

    # Verify structured dimension breakdown is present
    dim_scores = results[0]["dimension_scores"]
    assert DIMENSION_BUDGET in dim_scores
    assert DIMENSION_BEDROOM in dim_scores
    assert DIMENSION_AREA in dim_scores
    assert DIMENSION_LOCATION in dim_scores

    # Verify reasons list has 4 informative entries
    assert len(results[0]["reasons"]) == 4


@pytest.mark.django_db
def test_custom_dimension_weights(properties_setup):
    prop1, prop2, prop3, _ = properties_setup
    strategy = RuleBasedRecommendation()

    # Weight 100% on bedrooms
    preferences = {
        "bedrooms": 4,
        "weights": {"bedroom": 1.0, "budget": 0.0, "area": 0.0, "location": 0.0}
    }
    results = strategy.recommend([prop1, prop2, prop3], preferences)

    # prop2 is 4BHK so it should rank #1
    assert results[0]["property_id"] == prop2.id
    assert results[0]["score"] == 100.0


# ==============================================================================
# 3. API Endpoint Tests: /api/v1/recommendations/normal/
# ==============================================================================

@pytest.mark.django_db
def test_api_hard_constraint_price(api_client, properties_setup):
    prop1, prop2, prop3, _ = properties_setup

    # Ceiling 80L filters out prop2 (1.6 Cr)
    payload = {
        "preferences": {
            "max_price": 8000000,
            "bedrooms": 2,
        }
    }
    response = api_client.post("/api/v1/recommendations/normal/", payload, format='json')
    assert response.status_code == 200
    data = response.json()

    assert data["count"] == 2
    matched_ids = [r["property_id"] for r in data["results"]]
    assert prop1.id in matched_ids
    assert prop3.id in matched_ids
    assert prop2.id not in matched_ids
    assert data["applied_constraints"]["max_price"] == 8000000.0


@pytest.mark.django_db
def test_api_hard_constraint_exact_bedrooms(api_client, properties_setup):
    prop1, prop2, prop3, _ = properties_setup

    payload = {
        "preferences": {
            "bedrooms": 3,
            "exact_bedrooms": True,
        }
    }
    response = api_client.post("/api/v1/recommendations/normal/", payload, format='json')
    assert response.status_code == 200
    data = response.json()

    # Only prop1 has exactly 3 bedrooms
    assert data["count"] == 1
    assert data["results"][0]["property_id"] == prop1.id


@pytest.mark.django_db
def test_api_hard_constraint_property_type(api_client, properties_setup):
    prop1, prop2, prop3, _ = properties_setup

    payload = {
        "preferences": {
            "property_type": PropertyType.VILLA,
        }
    }
    response = api_client.post("/api/v1/recommendations/normal/", payload, format='json')
    assert response.status_code == 200
    data = response.json()

    assert data["count"] == 1
    assert data["results"][0]["property_id"] == prop2.id


@pytest.mark.django_db
def test_api_hard_constraint_spatial_area(api_client, properties_setup):
    prop1, prop2, prop3, area_salt_lake = properties_setup

    payload = {
        "preferences": {
            "area_id": area_salt_lake.id,
        }
    }
    response = api_client.post("/api/v1/recommendations/normal/", payload, format='json')
    assert response.status_code == 200
    data = response.json()

    # prop1 and prop2 are inside Salt Lake; prop3 is in Barasat
    assert data["count"] == 2
    matched_ids = [r["property_id"] for r in data["results"]]
    assert prop1.id in matched_ids
    assert prop2.id in matched_ids
    assert prop3.id not in matched_ids
    assert data["applied_constraints"]["area_id"] == area_salt_lake.id

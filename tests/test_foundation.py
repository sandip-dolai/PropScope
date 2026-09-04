# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
from django.contrib.auth import get_user_model
# pyrefly: ignore [missing-import]
from django.contrib.gis.geos import Point
# pyrefly: ignore [missing-import]
from django.contrib.gis.measure import D
from apps.accounts.models import UserRole
from apps.properties.models import Property, PropertyStatus, PropertyType
from apps.recommendations.strategies import RuleBasedRecommendation

User = get_user_model()


@pytest.mark.django_db
def test_user_roles():
    buyer = User.objects.create_user(username='test_buyer', password='password123', role=UserRole.BUYER)
    agent = User.objects.create_user(username='test_agent', password='password123', role=UserRole.AGENT)

    assert buyer.is_buyer is True
    assert buyer.is_agent is False
    assert agent.is_agent is True
    assert agent.is_buyer is False


@pytest.mark.django_db
def test_postgis_distance_query():
    agent = User.objects.create_user(username='prop_agent', password='password123', role=UserRole.AGENT)

    # Point A: Salt Lake (22.5840, 88.4250)
    prop1 = Property.objects.create(
        agent=agent,
        title="Salt Lake Flat",
        description="Close property",
        property_type=PropertyType.APARTMENT,
        status=PropertyStatus.ACTIVE,
        price=7500000.00,
        bedrooms=3,
        bathrooms=2,
        area_sqft=1400.00,
        address="Salt Lake",
        location=Point(88.4250, 22.5840, srid=4326)
    )

    # Point B: Far away (~15km away)
    prop2 = Property.objects.create(
        agent=agent,
        title="Far Away Villa",
        description="Distant property",
        property_type=PropertyType.VILLA,
        status=PropertyStatus.ACTIVE,
        price=15000000.00,
        bedrooms=4,
        bathrooms=4,
        area_sqft=2500.00,
        address="Far Out",
        location=Point(88.2500, 22.4500, srid=4326)
    )

    search_center = Point(88.4250, 22.5840, srid=4326)
    nearby_props = Property.objects.filter(
        status=PropertyStatus.ACTIVE,
        location__distance_lte=(search_center, D(km=5))
    )

    assert nearby_props.count() == 1
    assert nearby_props.first().id == prop1.id


@pytest.mark.django_db
def test_rule_based_recommendation():
    agent = User.objects.create_user(username='rec_agent', password='password123', role=UserRole.AGENT)

    p1 = Property.objects.create(
        agent=agent,
        title="Perfect 3BHK",
        description="Exact match",
        property_type=PropertyType.APARTMENT,
        price=7000000.00,
        bedrooms=3,
        bathrooms=2,
        area_sqft=1300.00,
        address="Address 1",
        location=Point(88.40, 22.58, srid=4326)
    )

    strategy = RuleBasedRecommendation()
    preferences = {"max_price": 8000000, "bedrooms": 3}
    results = strategy.recommend([p1], preferences)

    assert len(results) == 1
    assert results[0]["property_id"] == p1.id
    assert results[0]["normal_score"] > 80.0


@pytest.mark.django_db
def test_home_view_emits_csrf_cookie_and_meta(client):
    response = client.get('/')
    assert response.status_code == 200
    assert 'csrftoken' in response.cookies
    content = response.content.decode('utf-8')
    assert '<meta name="csrf-token"' in content
    assert 'window.apiClient' in content


@pytest.mark.django_db
def test_protected_polygon_search_with_csrf(client):
    # Obtain CSRF cookie first
    get_resp = client.get('/')
    csrf_cookie = get_resp.cookies['csrftoken'].value

    # Mutating POST with X-CSRFToken header
    geojson_polygon = {
        "type": "Polygon",
        "coordinates": [
            [
                [88.40, 22.56],
                [88.45, 22.56],
                [88.45, 22.60],
                [88.40, 22.60],
                [88.40, 22.56]
            ]
        ]
    }
    post_resp = client.post(
        '/api/v1/properties/polygon-search/',
        data={"geojson": geojson_polygon},
        content_type='application/json',
        HTTP_X_CSRFTOKEN=csrf_cookie
    )
    assert post_resp.status_code == 200


@pytest.mark.django_db
def test_asset_drawer_rendered_in_public_layout(client):
    response = client.get('/')
    assert response.status_code == 200
    content = response.content.decode('utf-8')
    assert 'id="assetDrawer"' in content
    assert 'id="assetDrawerBackdrop"' in content
    assert 'window.openAssetDrawer' in content
    assert 'proximityModal' not in content



# pyrefly: ignore [missing-import]
import pytest
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point, MultiPolygon, Polygon
from apps.accounts.models import UserRole
from apps.properties.models import Property, PropertyStatus, PropertyType
from apps.geography.models import Area

User = get_user_model()


@pytest.fixture
def agent_user(db):
    return User.objects.create_user(
        username='agent_metric_test',
        password='password123',
        role=UserRole.AGENT
    )


@pytest.fixture
def other_agent(db):
    return User.objects.create_user(
        username='agent_other_test',
        password='password123',
        role=UserRole.AGENT
    )


@pytest.fixture
def buyer_user(db):
    return User.objects.create_user(
        username='buyer_metric_test',
        password='password123',
        role=UserRole.BUYER
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username='admin_metric_test',
        password='password123',
        role=UserRole.ADMIN
    )


@pytest.fixture
def test_area(db):
    # Salt Lake bounding box polygon
    poly = Polygon(((88.40, 22.56), (88.44, 22.56), (88.44, 22.60), (88.40, 22.60), (88.40, 22.56)))
    return Area.objects.create(
        name='Salt Lake Sector V',
        city='Kolkata',
        boundary=MultiPolygon(poly)
    )


@pytest.fixture
def agent_properties(db, agent_user, other_agent, test_area):
    # 2 properties for agent_user (one inside area, one outside)
    p1 = Property.objects.create(
        agent=agent_user,
        title="Agent Flat 1",
        description="Test description",
        property_type=PropertyType.APARTMENT,
        status=PropertyStatus.ACTIVE,
        price=10000000.00,  # 1 Cr
        bedrooms=3,
        area_sqft=1000.00,  # 10,000 / sqft
        location=Point(88.42, 22.58, srid=4326)  # Inside test_area
    )
    p2 = Property.objects.create(
        agent=agent_user,
        title="Agent Flat 2",
        description="Test description",
        property_type=PropertyType.APARTMENT,
        status=PropertyStatus.ACTIVE,
        price=5000000.00,  # 50 Lakh
        bedrooms=2,
        area_sqft=500.00,   # 10,000 / sqft
        location=Point(88.50, 22.70, srid=4326)  # Outside test_area
    )
    # 1 property for other_agent
    p3 = Property.objects.create(
        agent=other_agent,
        title="Other Agent Flat",
        description="Test description",
        property_type=PropertyType.APARTMENT,
        status=PropertyStatus.ACTIVE,
        price=20000000.00,  # 2 Cr
        bedrooms=4,
        area_sqft=2000.00,
        location=Point(88.43, 22.59, srid=4326)  # Inside test_area
    )
    return p1, p2, p3


@pytest.mark.django_db
def test_dashboard_metrics_unauthenticated_blocked(client):
    resp = client.get('/api/v1/analytics/dashboard-metrics/')
    assert resp.status_code in [401, 403]


@pytest.mark.django_db
def test_dashboard_metrics_buyer_forbidden(client, buyer_user):
    client.force_login(buyer_user)
    resp = client.get('/api/v1/analytics/dashboard-metrics/')
    assert resp.status_code == 403


@pytest.mark.django_db
def test_dashboard_metrics_agent_scoped(client, agent_user, agent_properties, test_area):
    client.force_login(agent_user)
    resp = client.get('/api/v1/analytics/dashboard-metrics/')
    assert resp.status_code == 200

    data = resp.data
    assert data['scope_title'] == "Agent Managed Portfolio"
    assert data['metrics']['total_listings'] == 2
    assert data['metrics']['active_count'] == 2
    # 1 Cr + 50 L = 1.5 Cr
    assert data['metrics']['total_aum'] == 15000000.00
    assert "1.50 Cr" in data['metrics']['formatted_aum']

    # Submarket distribution: only 1 of agent's properties is inside test_area
    submarket = next((s for s in data['submarkets'] if s['id'] == test_area.id), None)
    assert submarket is not None
    assert submarket['count'] == 1


@pytest.mark.django_db
def test_dashboard_metrics_admin_platform_wide(client, admin_user, agent_properties, test_area):
    client.force_login(admin_user)
    resp = client.get('/api/v1/analytics/dashboard-metrics/')
    assert resp.status_code == 200

    data = resp.data
    assert data['scope_title'] == "Metropolitan Platform Portfolio"
    # Sees all 3 properties
    assert data['metrics']['total_listings'] == 3
    # 1 Cr + 50 L + 2 Cr = 3.5 Cr
    assert data['metrics']['total_aum'] == 35000000.00
    assert "3.50 Cr" in data['metrics']['formatted_aum']

    # Submarket: both p1 and p3 are inside test_area
    submarket = next((s for s in data['submarkets'] if s['id'] == test_area.id), None)
    assert submarket is not None
    assert submarket['count'] == 2


@pytest.mark.django_db
def test_dashboard_page_rendered(client, agent_user):
    client.force_login(agent_user)
    resp = client.get('/dashboard/')
    assert resp.status_code == 200
    content = resp.content.decode('utf-8')
    assert "Command Center" in content
    assert "Portfolio AUM" in content
    assert "Sub-Market Geographical Exposure" in content


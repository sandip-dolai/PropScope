# pyrefly: ignore [missing-import]
import pytest
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from apps.accounts.models import UserRole, AgentProfile
from apps.properties.models import Property, PropertyStatus, PropertyType

User = get_user_model()


@pytest.fixture
def accredited_agent(db):
    user = User.objects.create_user(
        username='accredited_agent',
        password='password123',
        email='agent@propscope.io',
        first_name='Priya',
        last_name='Mukherjee',
        phone_number='+919876543210',
        role=UserRole.AGENT
    )
    AgentProfile.objects.create(
        user=user,
        agency_name='North Bengal & Kolkata Realtors',
        license_number='WB-RERA-2024-5120',
        bio='Senior real estate advisor specializing in Kolkata and Barasat Metro spatial asset portfolios.'
    )
    return user


@pytest.fixture
def buyer_user(db):
    return User.objects.create_user(
        username='regular_buyer',
        password='password123',
        email='buyer@propscope.io',
        role=UserRole.BUYER
    )


@pytest.fixture
def agent_properties(db, accredited_agent):
    p1 = Property.objects.create(
        agent=accredited_agent,
        title='Luxury Penthouse Rajarhat',
        description='Exclusive terrace penthouse overlooking Eco Park',
        property_type=PropertyType.APARTMENT,
        status=PropertyStatus.ACTIVE,
        price=15000000.00,  # 1.50 Cr
        bedrooms=3,
        bathrooms=3,
        area_sqft=2200.0,
        address='Action Area II, Rajarhat, Kolkata',
        location=Point(88.4700, 22.6100, srid=4326)
    )
    p2 = Property.objects.create(
        agent=accredited_agent,
        title='Commercial Office Space Salt Lake',
        description='Grade A office space near Sector V Metro',
        property_type=PropertyType.COMMERCIAL,
        status=PropertyStatus.ACTIVE,
        price=25000000.00,  # 2.50 Cr
        bedrooms=1,
        bathrooms=2,
        area_sqft=3500.0,
        address='Sector V, Salt Lake, Kolkata',
        location=Point(88.4320, 22.5850, srid=4326)
    )
    # Inactive property (should NOT appear in public showcase)
    p3 = Property.objects.create(
        agent=accredited_agent,
        title='Archived Villa Barasat',
        description='Old archived listing',
        property_type=PropertyType.VILLA,
        status=PropertyStatus.INACTIVE,
        price=8000000.00,
        bedrooms=4,
        bathrooms=3,
        area_sqft=2800.0,
        address='Champadali, Barasat, Kolkata',
        location=Point(88.4800, 22.7200, srid=4326)
    )
    return [p1, p2, p3]


@pytest.mark.django_db
def test_agent_showcase_api_success(client, accredited_agent, agent_properties):
    url = f'/api/v1/auth/agents/{accredited_agent.id}/'
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    # Verify agent credentials
    assert data['agent']['id'] == accredited_agent.id
    assert data['agent']['full_name'] == 'Priya Mukherjee'
    assert data['agent']['agency_name'] == 'North Bengal & Kolkata Realtors'
    assert data['agent']['license_number'] == 'WB-RERA-2024-5120'
    assert data['agent']['monogram'] == 'PM'

    # Verify portfolio metrics
    stats = data['portfolio_stats']
    assert stats['active_listings_count'] == 2  # Only active listings
    assert stats['total_aum_inr'] == 40000000.0  # 1.5 Cr + 2.5 Cr
    assert stats['total_aum_crores'] == 4.0
    assert stats['average_price_lakhs'] == 200.0  # (1.5 Cr + 2.5 Cr) / 2 = 2 Cr = 200 Lakhs

    # Verify properties payload excludes archived listings
    assert len(data['properties']) == 2
    titles = [p['title'] for p in data['properties']]
    assert 'Luxury Penthouse Rajarhat' in titles
    assert 'Commercial Office Space Salt Lake' in titles
    assert 'Archived Villa Barasat' not in titles


@pytest.mark.django_db
def test_agent_showcase_api_404_for_non_agent(client, buyer_user):
    # Buyer ID should return 404
    res = client.get(f'/api/v1/auth/agents/{buyer_user.id}/')
    assert res.status_code == 404
    assert res.json()['error'] == 'Agent not found.'

    # Non-existent ID should return 404
    res_missing = client.get('/api/v1/auth/agents/99999/')
    assert res_missing.status_code == 404


@pytest.mark.django_db
def test_agent_showcase_html_page_render(client, accredited_agent, agent_properties):
    url = f'/agents/{accredited_agent.id}/'
    res = client.get(url)

    assert res.status_code == 200
    content = res.content.decode('utf-8')

    # Agent details present in SSR HTML
    assert 'Priya Mukherjee' in content
    assert 'North Bengal &amp; Kolkata Realtors' in content or 'North Bengal & Kolkata Realtors' in content
    assert 'WB-RERA-2024-5120' in content
    assert 'Luxury Penthouse Rajarhat' in content
    assert 'Commercial Office Space Salt Lake' in content
    assert 'Archived Villa Barasat' not in content
    assert 'Fit Bounds' in content


@pytest.mark.django_db
def test_agent_showcase_html_page_404_for_invalid(client, buyer_user):
    # Non-agent user returns 404
    res = client.get(f'/agents/{buyer_user.id}/')
    assert res.status_code == 404

    # Non-existent ID returns 404
    res_missing = client.get('/agents/99999/')
    assert res_missing.status_code == 404


@pytest.mark.django_db
def test_agent_showcase_empty_portfolio(client, accredited_agent):
    url = f'/agents/{accredited_agent.id}/'
    res = client.get(url)

    assert res.status_code == 200
    content = res.content.decode('utf-8')
    assert 'No Active Listings' in content

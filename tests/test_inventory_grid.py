# pyrefly: ignore [missing-import]
import pytest
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from apps.accounts.models import UserRole
from apps.properties.models import Property, PropertyStatus, PropertyType

User = get_user_model()


@pytest.fixture
def agent_one(db):
    return User.objects.create_user(
        username='agent_one_inv',
        password='password123',
        role=UserRole.AGENT,
        first_name='Agent',
        last_name='One'
    )


@pytest.fixture
def agent_two(db):
    return User.objects.create_user(
        username='agent_two_inv',
        password='password123',
        role=UserRole.AGENT,
        first_name='Agent',
        last_name='Two'
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username='admin_inv',
        password='password123',
        email='admin@propscope.io',
        role=UserRole.ADMIN
    )


@pytest.fixture
def buyer_user(db):
    return User.objects.create_user(
        username='buyer_inv',
        password='password123',
        role=UserRole.BUYER
    )


@pytest.fixture
def sample_portfolio(db, agent_one, agent_two):
    # Agent One properties
    p1 = Property.objects.create(
        agent=agent_one,
        title='Luxury Sky Penthouse',
        description='Panoramic urban penthouse in Sector V',
        property_type=PropertyType.APARTMENT,
        status=PropertyStatus.ACTIVE,
        price=18500000,
        bedrooms=3,
        bathrooms=3,
        area_sqft=2100,
        address='Sector V, Salt Lake, Kolkata',
        location=Point(88.4320, 22.5860, srid=4326)
    )
    p2 = Property.objects.create(
        agent=agent_one,
        title='Eco Green Villa',
        description='Private garden villa in Action Area 1',
        property_type=PropertyType.VILLA,
        status=PropertyStatus.UNDER_OFFER,
        price=27500000,
        bedrooms=4,
        bathrooms=4,
        area_sqft=3200,
        address='Action Area 1, New Town, Kolkata',
        location=Point(88.4650, 22.5890, srid=4326)
    )
    p3 = Property.objects.create(
        agent=agent_one,
        title='Cozy Studio Apartment',
        description='Compact studio near metro',
        property_type=PropertyType.APARTMENT,
        status=PropertyStatus.INACTIVE,
        price=4500000,
        bedrooms=1,
        bathrooms=1,
        area_sqft=550,
        address='Dum Dum Road, Kolkata',
        location=Point(88.4100, 22.6200, srid=4326)
    )

    # Agent Two properties
    p4 = Property.objects.create(
        agent=agent_two,
        title='Modern Commercial Office',
        description='Furnished office bay',
        property_type=PropertyType.COMMERCIAL,
        status=PropertyStatus.ACTIVE,
        price=32000000,
        bedrooms=0,
        bathrooms=2,
        area_sqft=2800,
        address='Rajarhat Main Road, Kolkata',
        location=Point(88.4500, 22.6100, srid=4326)
    )
    p5 = Property.objects.create(
        agent=agent_two,
        title='Heritage Independent House',
        description='Classic architecture residence',
        property_type=PropertyType.HOUSE,
        status=PropertyStatus.SOLD,
        price=14000000,
        bedrooms=3,
        bathrooms=2,
        area_sqft=1750,
        address='Barasat Central, Kolkata',
        location=Point(88.4800, 22.7200, srid=4326)
    )

    return [p1, p2, p3, p4, p5]


@pytest.mark.django_db
def test_inventory_api_unauthenticated_blocked(client):
    resp = client.get('/api/v1/properties/inventory/')
    assert resp.status_code in [401, 403]


@pytest.mark.django_db
def test_inventory_api_buyer_forbidden(client, buyer_user):
    client.force_login(buyer_user)
    resp = client.get('/api/v1/properties/inventory/')
    assert resp.status_code == 403
    assert "Only licensed agents" in resp.data.get('error', '')


@pytest.mark.django_db
def test_inventory_api_agent_isolation(client, agent_one, sample_portfolio):
    client.force_login(agent_one)
    resp = client.get('/api/v1/properties/inventory/')
    assert resp.status_code == 200
    data = resp.data

    # Agent One should see only their 3 listings
    assert data['count'] == 3
    assert len(data['results']) == 3

    # Check status counts across Agent One's portfolio
    sc = data['status_counts']
    assert sc['total'] == 3
    assert sc['active'] == 1
    assert sc['under_offer'] == 1
    assert sc['inactive'] == 1
    assert sc['sold'] == 0


@pytest.mark.django_db
def test_inventory_api_admin_platform_wide(client, admin_user, sample_portfolio):
    client.force_login(admin_user)
    resp = client.get('/api/v1/properties/inventory/')
    assert resp.status_code == 200
    data = resp.data

    # Admin sees all 5 listings across all agents
    assert data['count'] == 5
    assert data['status_counts']['total'] == 5
    assert data['status_counts']['active'] == 2
    assert data['status_counts']['under_offer'] == 1
    assert data['status_counts']['sold'] == 1
    assert data['status_counts']['inactive'] == 1


@pytest.mark.django_db
def test_inventory_api_search_and_filters(client, agent_one, sample_portfolio):
    client.force_login(agent_one)

    # 1. Search by title
    resp = client.get('/api/v1/properties/inventory/?search=Penthouse')
    assert resp.status_code == 200
    assert resp.data['count'] == 1
    assert resp.data['results'][0]['title'] == 'Luxury Sky Penthouse'

    # 2. Search by address
    resp = client.get('/api/v1/properties/inventory/?search=Dum Dum')
    assert resp.status_code == 200
    assert resp.data['count'] == 1
    assert resp.data['results'][0]['title'] == 'Cozy Studio Apartment'

    # 3. Filter by status
    resp = client.get('/api/v1/properties/inventory/?status=UNDER_OFFER')
    assert resp.status_code == 200
    assert resp.data['count'] == 1
    assert resp.data['results'][0]['status'] == 'UNDER_OFFER'

    # 4. Filter by bedrooms
    resp = client.get('/api/v1/properties/inventory/?bedrooms=4')
    assert resp.status_code == 200
    assert resp.data['count'] == 1
    assert resp.data['results'][0]['bedrooms'] >= 4

    # 5. Filter by property type
    resp = client.get('/api/v1/properties/inventory/?property_type=VILLA')
    assert resp.status_code == 200
    assert resp.data['count'] == 1
    assert resp.data['results'][0]['property_type'] == 'VILLA'

    # 6. Ordering by price descending
    resp = client.get('/api/v1/properties/inventory/?ordering=-price')
    assert resp.status_code == 200
    results = resp.data['results']
    assert len(results) == 3
    assert float(results[0]['price']) >= float(results[1]['price']) >= float(results[2]['price'])


@pytest.mark.django_db
def test_inventory_inline_status_patch(client, agent_one, sample_portfolio):
    client.force_login(agent_one)
    target_prop = sample_portfolio[0]  # Currently ACTIVE
    assert target_prop.status == PropertyStatus.ACTIVE

    # Change to UNDER_OFFER
    resp = client.patch(
        f'/api/v1/properties/{target_prop.id}/',
        {'status': 'UNDER_OFFER'},
        content_type='application/json'
    )
    assert resp.status_code == 200
    target_prop.refresh_from_db()
    assert target_prop.status == PropertyStatus.UNDER_OFFER

    # Change to SOLD
    resp = client.patch(
        f'/api/v1/properties/{target_prop.id}/',
        {'status': 'SOLD'},
        content_type='application/json'
    )
    assert resp.status_code == 200
    target_prop.refresh_from_db()
    assert target_prop.status == PropertyStatus.SOLD


@pytest.mark.django_db
def test_inventory_inline_price_patch(client, agent_one, sample_portfolio):
    client.force_login(agent_one)
    target_prop = sample_portfolio[0]

    resp = client.patch(
        f'/api/v1/properties/{target_prop.id}/',
        {'price': 19500000},
        content_type='application/json'
    )
    assert resp.status_code == 200
    target_prop.refresh_from_db()
    assert target_prop.price == 19500000


@pytest.mark.django_db
def test_inventory_unauthorized_patch_blocked(client, agent_two, sample_portfolio):
    # Agent Two attempts to modify Agent One's property
    client.force_login(agent_two)
    agent_one_prop = sample_portfolio[0]

    resp = client.patch(
        f'/api/v1/properties/{agent_one_prop.id}/',
        {'status': 'INACTIVE'},
        content_type='application/json'
    )
    assert resp.status_code == 403
    agent_one_prop.refresh_from_db()
    assert agent_one_prop.status != PropertyStatus.INACTIVE


@pytest.mark.django_db
def test_inventory_page_rendered(client, agent_one):
    client.force_login(agent_one)
    resp = client.get('/dashboard/inventory/')
    assert resp.status_code == 200
    content = resp.content.decode('utf-8')
    assert 'Asset Inventory Management' in content
    assert 'inventoryTable' in content
    assert 'inventorySearchInput' in content

# pyrefly: ignore [missing-import]
import pytest
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from apps.accounts.models import UserRole, AgentProfile
from apps.properties.models import Property, PropertyStatus, PropertyType

User = get_user_model()


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username='gov_admin',
        password='password123',
        email='admin@propscope.io',
        role=UserRole.ADMIN,
        first_name='System',
        last_name='Admin'
    )


@pytest.fixture
def agent_one(db):
    user = User.objects.create_user(
        username='agent_one',
        password='password123',
        email='agent1@propscope.io',
        role=UserRole.AGENT,
        first_name='Agent',
        last_name='One'
    )
    AgentProfile.objects.create(
        user=user,
        agency_name='Kolkata Realty Co',
        license_number='WB-RERA-2024-1001',
        is_verified=False
    )
    return user


@pytest.fixture
def agent_two(db):
    user = User.objects.create_user(
        username='agent_two',
        password='password123',
        email='agent2@propscope.io',
        role=UserRole.AGENT,
        first_name='Agent',
        last_name='Two'
    )
    AgentProfile.objects.create(
        user=user,
        agency_name='Bengal Estates',
        license_number='WB-RERA-2024-2002',
        is_verified=True
    )
    return user


@pytest.fixture
def buyer_user(db):
    return User.objects.create_user(
        username='buyer_user',
        password='password123',
        email='buyer@propscope.io',
        role=UserRole.BUYER
    )


@pytest.fixture
def sample_properties(db, agent_one):
    p_pending = Property.objects.create(
        agent=agent_one,
        title='Pending Moderation Apartment',
        description='New listing submitted for review',
        property_type=PropertyType.APARTMENT,
        status=PropertyStatus.PENDING_APPROVAL,
        price=7500000.00,
        bedrooms=3,
        bathrooms=2,
        area_sqft=1450.0,
        address='Action Area I, New Town, Kolkata',
        location=Point(88.4600, 22.5900, srid=4326)
    )
    p_active = Property.objects.create(
        agent=agent_one,
        title='Active Market Villa',
        description='Published approved villa',
        property_type=PropertyType.VILLA,
        status=PropertyStatus.ACTIVE,
        price=18000000.00,
        bedrooms=4,
        bathrooms=4,
        area_sqft=3200.0,
        address='Sector III, Salt Lake, Kolkata',
        location=Point(88.4150, 22.5700, srid=4326)
    )
    return [p_pending, p_active]


@pytest.mark.django_db
def test_admin_stats_unauthorized_blocked(client, buyer_user):
    url = '/api/v1/properties/admin/moderation/stats/'

    # Anonymous user blocked
    res_anon = client.get(url)
    assert res_anon.status_code in [401, 403]

    # Buyer blocked
    client.force_login(buyer_user)
    res_buyer = client.get(url)
    assert res_buyer.status_code == 403


@pytest.mark.django_db
def test_admin_stats_agent_forbidden(client, agent_one):
    url = '/api/v1/properties/admin/moderation/stats/'
    client.force_login(agent_one)
    res = client.get(url)
    assert res.status_code == 403


@pytest.mark.django_db
def test_admin_stats_admin_success(client, admin_user, agent_one, agent_two, sample_properties):
    client.force_login(admin_user)
    url = '/api/v1/properties/admin/moderation/stats/'
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()

    assert data['total_properties'] == 2
    assert data['pending_properties'] == 1
    assert data['active_properties'] == 1
    assert data['total_aum_crores'] == 1.8  # Only active property (1.80 Cr)
    assert data['total_agents'] == 2
    assert data['verified_agents'] == 1  # agent_two is verified
    assert data['compliance_percentage'] == 50.0  # 1/2 = 50%
    assert len(data['submarkets']) >= 1


@pytest.mark.django_db
def test_admin_property_moderation_queue(client, admin_user, sample_properties):
    client.force_login(admin_user)
    url = '/api/v1/properties/admin/moderation/properties/?status=PENDING_APPROVAL'
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()
    assert data['count'] == 1
    assert data['results'][0]['title'] == 'Pending Moderation Apartment'
    assert data['results'][0]['status'] == 'PENDING_APPROVAL'

    # Filter for active
    res_active = client.get('/api/v1/properties/admin/moderation/properties/?status=ACTIVE')
    assert res_active.status_code == 200
    assert res_active.json()['count'] == 1
    assert res_active.json()['results'][0]['title'] == 'Active Market Villa'


@pytest.mark.django_db
def test_admin_property_approve_decision(client, admin_user, sample_properties):
    client.force_login(admin_user)
    pending_prop = sample_properties[0]
    assert pending_prop.status == PropertyStatus.PENDING_APPROVAL

    url = f'/api/v1/properties/admin/moderation/properties/{pending_prop.id}/decision/'
    res = client.post(url, data={'action': 'approve'}, content_type='application/json')

    assert res.status_code == 200
    pending_prop.refresh_from_db()
    assert pending_prop.status == PropertyStatus.ACTIVE
    assert 'approved and published' in res.json()['message']


@pytest.mark.django_db
def test_admin_property_reject_decision(client, admin_user, sample_properties):
    client.force_login(admin_user)
    pending_prop = sample_properties[0]

    url = f'/api/v1/properties/admin/moderation/properties/{pending_prop.id}/decision/'
    res = client.post(url, data={'action': 'reject'}, content_type='application/json')

    assert res.status_code == 200
    pending_prop.refresh_from_db()
    assert pending_prop.status == PropertyStatus.INACTIVE
    assert 'rejected and archived' in res.json()['message']


@pytest.mark.django_db
def test_admin_agent_list_and_verify_toggle(client, admin_user, agent_one):
    client.force_login(admin_user)

    # List agents
    res_list = client.get('/api/v1/properties/admin/moderation/agents/')
    assert res_list.status_code == 200
    data = res_list.json()
    assert data['count'] >= 1

    # agent_one starts unverified
    assert agent_one.agent_profile.is_verified is False

    # Toggle verification
    verify_url = f'/api/v1/properties/admin/moderation/agents/{agent_one.id}/verify/'
    res_verify = client.post(verify_url, content_type='application/json')
    assert res_verify.status_code == 200

    agent_one.agent_profile.refresh_from_db()
    assert agent_one.agent_profile.is_verified is True
    assert res_verify.json()['agent']['is_verified'] is True

    # Toggle back to unverified
    res_unverify = client.post(verify_url, content_type='application/json')
    assert res_unverify.status_code == 200
    agent_one.agent_profile.refresh_from_db()
    assert agent_one.agent_profile.is_verified is False


@pytest.mark.django_db
def test_admin_console_page_access_control(client, admin_user, agent_one, buyer_user):
    url = '/dashboard/admin/'

    # Admin access allowed
    client.force_login(admin_user)
    res_admin = client.get(url)
    assert res_admin.status_code == 200
    content = res_admin.content.decode('utf-8')
    assert 'Metropolitan Asset Moderation &amp; Audit Console' in content or 'Metropolitan Asset Moderation & Audit Console' in content

    # Agent access forbidden (403)
    client.force_login(agent_one)
    res_agent = client.get(url)
    assert res_agent.status_code == 403

    # Buyer access forbidden (403)
    client.force_login(buyer_user)
    res_buyer = client.get(url)
    assert res_buyer.status_code == 403

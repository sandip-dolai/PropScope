# pyrefly: ignore [missing-import]
import pytest
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from apps.accounts.models import UserRole
from apps.properties.models import Property, PropertyStatus, PropertyType, PropertyInquiry, InquiryStatus

User = get_user_model()


@pytest.fixture
def agent_one(db):
    return User.objects.create_user(
        username='agent_lead_one',
        password='password123',
        role=UserRole.AGENT,
        first_name='Agent',
        last_name='One'
    )


@pytest.fixture
def agent_two(db):
    return User.objects.create_user(
        username='agent_lead_two',
        password='password123',
        role=UserRole.AGENT,
        first_name='Agent',
        last_name='Two'
    )


@pytest.fixture
def buyer_user(db):
    return User.objects.create_user(
        username='buyer_lead_test',
        password='password123',
        email='buyer@propscope.io',
        first_name='Rahul',
        last_name='Sen',
        role=UserRole.BUYER
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username='admin_lead_test',
        password='password123',
        email='admin@propscope.io',
        role=UserRole.ADMIN
    )


@pytest.fixture
def property_one(db, agent_one):
    return Property.objects.create(
        agent=agent_one,
        title='Salt Lake Luxury Villa',
        description='Spacious villa',
        property_type=PropertyType.VILLA,
        status=PropertyStatus.ACTIVE,
        price=22500000,
        bedrooms=4,
        bathrooms=3,
        area_sqft=2800,
        address='Sector 1, Salt Lake, Kolkata',
        location=Point(88.4100, 22.5850, srid=4326)
    )


@pytest.fixture
def property_two(db, agent_two):
    return Property.objects.create(
        agent=agent_two,
        title='New Town High-Rise Apartment',
        description='Modern flat',
        property_type=PropertyType.APARTMENT,
        status=PropertyStatus.ACTIVE,
        price=9500000,
        bedrooms=3,
        bathrooms=2,
        area_sqft=1450,
        address='Action Area 2, New Town, Kolkata',
        location=Point(88.4600, 22.5900, srid=4326)
    )


@pytest.mark.django_db
def test_inquire_public_success(client, property_one):
    payload = {
        'name': 'Pooja Verma',
        'email': 'pooja@example.com',
        'phone': '+91 98300 12345',
        'message': 'Interested in viewing this villa on Sunday.',
        'preferred_visit_date': '2026-09-15'
    }
    resp = client.post(
        f'/api/v1/properties/{property_one.id}/inquire/',
        payload,
        content_type='application/json'
    )
    assert resp.status_code == 201
    assert 'inquiry' in resp.data
    assert resp.data['inquiry']['name'] == 'Pooja Verma'
    assert resp.data['inquiry']['status'] == InquiryStatus.NEW

    # Verify saved in DB
    inquiry = PropertyInquiry.objects.get(pk=resp.data['inquiry']['id'])
    assert inquiry.property == property_one
    assert inquiry.buyer is None
    assert str(inquiry.preferred_visit_date) == '2026-09-15'


@pytest.mark.django_db
def test_inquire_authenticated_buyer_autofill(client, buyer_user, property_one):
    client.force_login(buyer_user)
    payload = {
        'phone': '+91 98311 55555',
        'message': 'Can I negotiate on price?',
        'preferred_visit_date': '2026-09-18'
    }
    resp = client.post(
        f'/api/v1/properties/{property_one.id}/inquire/',
        payload,
        content_type='application/json'
    )
    assert resp.status_code == 201
    inquiry = PropertyInquiry.objects.get(pk=resp.data['inquiry']['id'])
    assert inquiry.buyer == buyer_user
    assert inquiry.name == 'Rahul Sen'
    assert inquiry.email == 'buyer@propscope.io'


@pytest.mark.django_db
def test_inquire_nonexistent_property(client):
    resp = client.post(
        '/api/v1/properties/99999/inquire/',
        {'name': 'Test', 'email': 'test@test.com'},
        content_type='application/json'
    )
    assert resp.status_code == 404


@pytest.mark.django_db
def test_leads_api_unauthenticated_blocked(client):
    resp = client.get('/api/v1/properties/leads/')
    assert resp.status_code in [401, 403]


@pytest.mark.django_db
def test_leads_api_buyer_forbidden(client, buyer_user):
    client.force_login(buyer_user)
    resp = client.get('/api/v1/properties/leads/')
    assert resp.status_code == 403


@pytest.mark.django_db
def test_leads_api_agent_isolation(client, agent_one, agent_two, property_one, property_two):
    # Create 2 leads for Agent One's property
    l1 = PropertyInquiry.objects.create(
        property=property_one,
        name='Buyer Alpha',
        email='alpha@test.com',
        phone='9999999991',
        status=InquiryStatus.NEW
    )
    l2 = PropertyInquiry.objects.create(
        property=property_one,
        name='Buyer Beta',
        email='beta@test.com',
        phone='9999999992',
        status=InquiryStatus.SITE_VISIT
    )

    # Create 1 lead for Agent Two's property
    l3 = PropertyInquiry.objects.create(
        property=property_two,
        name='Buyer Gamma',
        email='gamma@test.com',
        phone='9999999993',
        status=InquiryStatus.CONTACTED
    )

    # Agent One should see only l1 and l2
    client.force_login(agent_one)
    resp1 = client.get('/api/v1/properties/leads/')
    assert resp1.status_code == 200
    assert resp1.data['count'] == 2
    assert resp1.data['status_counts']['total'] == 2
    assert resp1.data['status_counts']['new'] == 1
    assert resp1.data['status_counts']['site_visit'] == 1
    assert resp1.data['status_counts']['contacted'] == 0

    # Agent Two should see only l3
    client.force_login(agent_two)
    resp2 = client.get('/api/v1/properties/leads/')
    assert resp2.status_code == 200
    assert resp2.data['count'] == 1
    assert resp2.data['status_counts']['total'] == 1
    assert resp2.data['status_counts']['contacted'] == 1


@pytest.mark.django_db
def test_leads_api_admin_platform_wide(client, admin_user, property_one, property_two):
    PropertyInquiry.objects.create(
        property=property_one,
        name='Buyer One',
        email='b1@test.com',
        status=InquiryStatus.NEW
    )
    PropertyInquiry.objects.create(
        property=property_two,
        name='Buyer Two',
        email='b2@test.com',
        status=InquiryStatus.CLOSED
    )

    client.force_login(admin_user)
    resp = client.get('/api/v1/properties/leads/')
    assert resp.status_code == 200
    assert resp.data['count'] == 2
    assert resp.data['status_counts']['total'] == 2
    assert resp.data['status_counts']['new'] == 1
    assert resp.data['status_counts']['closed'] == 1


@pytest.mark.django_db
def test_leads_api_search_and_filter(client, agent_one, property_one):
    PropertyInquiry.objects.create(
        property=property_one,
        name='Vikram Sharma',
        email='vikram@test.com',
        phone='9830111111',
        status=InquiryStatus.NEW
    )
    PropertyInquiry.objects.create(
        property=property_one,
        name='Ananya Roy',
        email='ananya@test.com',
        phone='9830222222',
        status=InquiryStatus.SITE_VISIT
    )

    client.force_login(agent_one)

    # Filter by status
    resp_status = client.get('/api/v1/properties/leads/?status=SITE_VISIT')
    assert resp_status.status_code == 200
    assert resp_status.data['count'] == 1
    assert resp_status.data['results'][0]['name'] == 'Ananya Roy'

    # Search by name
    resp_search = client.get('/api/v1/properties/leads/?search=Vikram')
    assert resp_search.status_code == 200
    assert resp_search.data['count'] == 1
    assert resp_search.data['results'][0]['name'] == 'Vikram Sharma'


@pytest.mark.django_db
def test_lead_status_and_notes_patch(client, agent_one, property_one):
    lead = PropertyInquiry.objects.create(
        property=property_one,
        name='Test Buyer',
        email='test@buyer.com',
        status=InquiryStatus.NEW
    )

    client.force_login(agent_one)
    resp = client.patch(
        f'/api/v1/properties/leads/{lead.id}/',
        {'status': 'SITE_VISIT', 'agent_notes': 'Scheduled walkthrough for Saturday 4 PM.'},
        content_type='application/json'
    )
    assert resp.status_code == 200
    lead.refresh_from_db()
    assert lead.status == InquiryStatus.SITE_VISIT
    assert lead.agent_notes == 'Scheduled walkthrough for Saturday 4 PM.'


@pytest.mark.django_db
def test_lead_unauthorized_patch_blocked(client, agent_two, property_one):
    # Lead belongs to agent_one's property
    lead = PropertyInquiry.objects.create(
        property=property_one,
        name='Test Buyer',
        email='test@buyer.com',
        status=InquiryStatus.NEW
    )

    # Agent two tries to modify
    client.force_login(agent_two)
    resp = client.patch(
        f'/api/v1/properties/leads/{lead.id}/',
        {'status': 'LOST'},
        content_type='application/json'
    )
    assert resp.status_code == 403
    lead.refresh_from_db()
    assert lead.status == InquiryStatus.NEW


@pytest.mark.django_db
def test_lead_delete(client, agent_one, property_one):
    lead = PropertyInquiry.objects.create(
        property=property_one,
        name='Lead to delete',
        email='del@test.com'
    )
    client.force_login(agent_one)
    resp = client.delete(f'/api/v1/properties/leads/{lead.id}/')
    assert resp.status_code == 200
    assert not PropertyInquiry.objects.filter(pk=lead.id).exists()


@pytest.mark.django_db
def test_leads_dashboard_page_rendered(client, agent_one):
    client.force_login(agent_one)
    resp = client.get('/dashboard/leads/')
    assert resp.status_code == 200
    content = resp.content.decode('utf-8')
    assert 'Buyer Inquiries & Sales Pipeline' in content
    assert 'leadsTable' in content
    assert 'leadsSearchInput' in content

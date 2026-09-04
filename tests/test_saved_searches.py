# pyrefly: ignore [missing-import]
import pytest
from django.contrib.auth import get_user_model
from apps.accounts.models import UserRole
from apps.saved_searches.models import SavedSearch

User = get_user_model()


@pytest.fixture
def buyer_user(db):
    return User.objects.create_user(
        username='buyer_searcher',
        password='password123',
        role=UserRole.BUYER
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        username='other_buyer',
        password='password123',
        role=UserRole.BUYER
    )


@pytest.mark.django_db
def test_saved_search_unauthenticated_blocked(client):
    response = client.get('/api/v1/saved-searches/')
    assert response.status_code in [401, 403]

    response = client.post(
        '/api/v1/saved-searches/',
        {'title': 'Test', 'criteria': {}},
        content_type='application/json'
    )
    assert response.status_code in [401, 403]


@pytest.mark.django_db
def test_saved_search_lifecycle(client, buyer_user):
    client.force_login(buyer_user)

    # 1. Initial list should be empty
    resp = client.get('/api/v1/saved-searches/')
    assert resp.status_code == 200
    assert len(resp.data) == 0

    # 2. Create a radius search
    payload = {
        'title': '3 BHK within 5km New Town',
        'criteria': {
            'mode': 'radius',
            'bhk': '3',
            'params': {
                'lat': 22.5850,
                'lng': 88.4700,
                'radius_km': 5.0
            },
            'summary': '3 BHK within 5.0 km radius'
        }
    }
    create_resp = client.post(
        '/api/v1/saved-searches/',
        payload,
        content_type='application/json'
    )
    assert create_resp.status_code == 201
    search_id = create_resp.data['id']
    assert create_resp.data['title'] == '3 BHK within 5km New Town'
    assert create_resp.data['criteria']['mode'] == 'radius'

    # 3. List should have 1 item
    list_resp = client.get('/api/v1/saved-searches/')
    assert list_resp.status_code == 200
    assert len(list_resp.data) == 1
    assert list_resp.data[0]['id'] == search_id

    # 4. Retrieve single detail
    detail_resp = client.get(f'/api/v1/saved-searches/{search_id}/')
    assert detail_resp.status_code == 200
    assert detail_resp.data['id'] == search_id

    # 5. Delete saved search
    del_resp = client.delete(f'/api/v1/saved-searches/{search_id}/')
    assert del_resp.status_code == 204
    assert not SavedSearch.objects.filter(id=search_id).exists()

    # 6. List is empty again
    list_after = client.get('/api/v1/saved-searches/')
    assert len(list_after.data) == 0


@pytest.mark.django_db
def test_saved_search_user_isolation(client, buyer_user, other_user):
    # Buyer creates a search
    client.force_login(buyer_user)
    create_resp = client.post(
        '/api/v1/saved-searches/',
        {
            'title': 'Private Buyer Search',
            'criteria': {'mode': 'all'}
        },
        content_type='application/json'
    )
    search_id = create_resp.data['id']

    # Other user logs in
    client.force_login(other_user)

    # Other user's list does not show buyer's search
    other_list = client.get('/api/v1/saved-searches/')
    assert len(other_list.data) == 0

    # Other user cannot retrieve buyer's search
    other_get = client.get(f'/api/v1/saved-searches/{search_id}/')
    assert other_get.status_code == 404

    # Other user cannot delete buyer's search
    other_del = client.delete(f'/api/v1/saved-searches/{search_id}/')
    assert other_del.status_code == 404


@pytest.mark.django_db
def test_saved_search_polygon_and_submarket_criteria(client, buyer_user):
    client.force_login(buyer_user)
    payload = {
        'title': 'Dum Dum 2 BHK & Salt Lake Corridor',
        'criteria': {
            'mode': 'submarket',
            'bhk': '2',
            'params': {
                'area_id': 2,
                'area_name': 'Dum Dum'
            },
            'summary': '2 BHK in Dum Dum'
        }
    }
    resp = client.post('/api/v1/saved-searches/', payload, content_type='application/json')
    assert resp.status_code == 201
    assert resp.data['criteria']['params']['area_name'] == 'Dum Dum'
    assert resp.data['criteria']['bhk'] == '2'


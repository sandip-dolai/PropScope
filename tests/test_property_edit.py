# pyrefly: ignore [missing-import]
import io
import pytest
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from apps.accounts.models import UserRole
from apps.properties.models import Property, PropertyStatus, PropertyType, PropertyImage

User = get_user_model()


def generate_test_image():
    file = io.BytesIO()
    image = Image.new('RGB', (100, 100), color='green')
    image.save(file, 'jpeg')
    file.seek(0)
    return SimpleUploadedFile('test_photo.jpg', file.read(), content_type='image/jpeg')


@pytest.fixture
def owner_agent(db):
    return User.objects.create_user(
        username='agent_owner_edit',
        password='password123',
        role=UserRole.AGENT,
        first_name='Owner',
        last_name='Agent'
    )


@pytest.fixture
def other_agent(db):
    return User.objects.create_user(
        username='agent_other_edit',
        password='password123',
        role=UserRole.AGENT,
        first_name='Other',
        last_name='Agent'
    )


@pytest.fixture
def buyer_user(db):
    return User.objects.create_user(
        username='buyer_intruder_edit',
        password='password123',
        role=UserRole.BUYER
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username='admin_supervisor_edit',
        password='password123',
        email='admin_edit@propscope.io',
        role=UserRole.ADMIN
    )


@pytest.fixture
def sample_property(db, owner_agent):
    return Property.objects.create(
        agent=owner_agent,
        title='Modern Duplex Villa',
        description='Luxurious duplex in Salt Lake',
        property_type=PropertyType.VILLA,
        status=PropertyStatus.ACTIVE,
        price=18500000,
        bedrooms=4,
        bathrooms=3,
        area_sqft=2600,
        address='Sector 1, Salt Lake, Kolkata',
        location=Point(88.4100, 22.5850, srid=4326)
    )


@pytest.mark.django_db
def test_property_edit_agent_owner_success(client, owner_agent, sample_property):
    client.force_login(owner_agent)
    payload = {
        'title': 'Renovated Luxury Duplex Villa',
        'price': 19500000,
        'bedrooms': 5,
        'latitude': 22.5900,
        'longitude': 88.4200
    }
    resp = client.patch(
        f'/api/v1/properties/{sample_property.id}/',
        payload,
        content_type='application/json'
    )
    assert resp.status_code == 200
    sample_property.refresh_from_db()
    assert sample_property.title == 'Renovated Luxury Duplex Villa'
    assert sample_property.price == 19500000
    assert sample_property.bedrooms == 5
    assert round(sample_property.location.y, 4) == 22.5900
    assert round(sample_property.location.x, 4) == 88.4200


@pytest.mark.django_db
def test_property_edit_other_agent_forbidden(client, other_agent, sample_property):
    client.force_login(other_agent)
    resp = client.patch(
        f'/api/v1/properties/{sample_property.id}/',
        {'title': 'Hacked Title'},
        content_type='application/json'
    )
    assert resp.status_code == 403
    sample_property.refresh_from_db()
    assert sample_property.title != 'Hacked Title'


@pytest.mark.django_db
def test_property_edit_buyer_forbidden(client, buyer_user, sample_property):
    client.force_login(buyer_user)
    resp = client.patch(
        f'/api/v1/properties/{sample_property.id}/',
        {'price': 100000},
        content_type='application/json'
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_property_edit_admin_success(client, admin_user, sample_property):
    client.force_login(admin_user)
    resp = client.patch(
        f'/api/v1/properties/{sample_property.id}/',
        {'status': 'SOLD'},
        content_type='application/json'
    )
    assert resp.status_code == 200
    sample_property.refresh_from_db()
    assert sample_property.status == PropertyStatus.SOLD


@pytest.mark.django_db
def test_property_image_upload_and_primary(client, owner_agent, sample_property):
    client.force_login(owner_agent)
    image_file = generate_test_image()

    resp = client.post(
        f'/api/v1/properties/{sample_property.id}/images/',
        {'image': image_file, 'caption': 'Front Elevation'},
        format='multipart'
    )
    assert resp.status_code == 201
    assert len(resp.data) == 1
    assert resp.data[0]['is_primary'] is True  # First image is auto-promoted to primary
    assert resp.data[0]['caption'] == 'Front Elevation'

    # Verify in database
    img_record = PropertyImage.objects.get(pk=resp.data[0]['id'])
    assert img_record.property == sample_property
    assert img_record.is_primary is True


@pytest.mark.django_db
def test_property_image_primary_toggle(client, owner_agent, sample_property):
    client.force_login(owner_agent)
    img1 = PropertyImage.objects.create(
        property=sample_property,
        image=generate_test_image(),
        is_primary=True
    )
    img2 = PropertyImage.objects.create(
        property=sample_property,
        image=generate_test_image(),
        is_primary=False
    )

    # Set img2 as primary
    resp = client.patch(
        f'/api/v1/properties/{sample_property.id}/images/{img2.id}/',
        {'is_primary': True},
        content_type='application/json'
    )
    assert resp.status_code == 200
    img1.refresh_from_db()
    img2.refresh_from_db()
    assert img2.is_primary is True
    assert img1.is_primary is False


@pytest.mark.django_db
def test_property_image_delete(client, owner_agent, sample_property):
    client.force_login(owner_agent)
    img = PropertyImage.objects.create(
        property=sample_property,
        image=generate_test_image(),
        is_primary=True
    )

    resp = client.delete(f'/api/v1/properties/{sample_property.id}/images/{img.id}/')
    assert resp.status_code == 200
    assert not PropertyImage.objects.filter(pk=img.id).exists()


@pytest.mark.django_db
def test_property_image_unauthorized_upload_blocked(client, other_agent, sample_property):
    client.force_login(other_agent)
    image_file = generate_test_image()
    resp = client.post(
        f'/api/v1/properties/{sample_property.id}/images/',
        {'image': image_file},
        format='multipart'
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_property_delete_lifecycle(client, owner_agent, sample_property):
    client.force_login(owner_agent)
    resp = client.delete(f'/api/v1/properties/{sample_property.id}/')
    assert resp.status_code == 204
    assert not Property.objects.filter(pk=sample_property.id).exists()


@pytest.mark.django_db
def test_property_edit_page_rendered(client, owner_agent, other_agent, sample_property):
    # Owner agent accesses edit page
    client.force_login(owner_agent)
    resp = client.get(f'/dashboard/properties/{sample_property.id}/edit/')
    assert resp.status_code == 200
    content = resp.content.decode('utf-8')
    assert sample_property.title in content
    assert 'editPinMap' in content
    assert 'galleryGrid' in content

    # Non-owner agent accesses edit page -> PermissionDenied (403)
    client.force_login(other_agent)
    resp_other = client.get(f'/dashboard/properties/{sample_property.id}/edit/')
    assert resp_other.status_code == 403

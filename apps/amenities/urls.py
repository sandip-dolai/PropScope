from django.urls import path
from .views import AmenityCategoryListView, AmenityListView, AmenityNearbyView

app_name = 'amenities'

urlpatterns = [
    path('', AmenityListView.as_view(), name='amenity_list'),
    path('categories/', AmenityCategoryListView.as_view(), name='amenity_categories'),
    path('nearby/', AmenityNearbyView.as_view(), name='amenity_nearby'),
]

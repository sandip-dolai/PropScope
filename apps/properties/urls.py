from django.urls import path
from .views import (
    PropertyListCreateView,
    PropertyDetailView,
    PropertyRadiusSearchView,
    PropertyPolygonSearchView,
    PropertyBoundingBoxSearchView
)

app_name = 'properties'

urlpatterns = [
    path('', PropertyListCreateView.as_view(), name='property_list_create'),
    path('<int:pk>/', PropertyDetailView.as_view(), name='property_detail'),
    path('radius-search/', PropertyRadiusSearchView.as_view(), name='property_radius_search'),
    path('polygon-search/', PropertyPolygonSearchView.as_view(), name='property_polygon_search'),
    path('bbox-search/', PropertyBoundingBoxSearchView.as_view(), name='property_bbox_search'),
]

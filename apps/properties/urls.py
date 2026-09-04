from django.urls import path
from .views import (
    PropertyListCreateView,
    PropertyDetailView,
    PropertyRadiusSearchView,
    PropertyPolygonSearchView,
    PropertyBoundingBoxSearchView,
    PropertyNearestAmenitiesView,
    AgentInventoryAPIView,
)

app_name = 'properties'

urlpatterns = [
    path('', PropertyListCreateView.as_view(), name='property_list_create'),
    path('inventory/', AgentInventoryAPIView.as_view(), name='property_inventory_api'),
    path('<int:pk>/', PropertyDetailView.as_view(), name='property_detail'),
    path('<int:pk>/nearest-amenities/', PropertyNearestAmenitiesView.as_view(), name='property_nearest_amenities'),
    path('radius-search/', PropertyRadiusSearchView.as_view(), name='property_radius_search'),
    path('polygon-search/', PropertyPolygonSearchView.as_view(), name='property_polygon_search'),
    path('bbox-search/', PropertyBoundingBoxSearchView.as_view(), name='property_bbox_search'),
]

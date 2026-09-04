from django.urls import path
from .views import (
    PropertyListCreateView,
    PropertyDetailView,
    PropertyRadiusSearchView,
    PropertyPolygonSearchView,
    PropertyBoundingBoxSearchView,
    PropertyNearestAmenitiesView,
    AgentInventoryAPIView,
    PropertyImageUploadView,
    PropertyImageDetailView,
    PropertyInquiryCreateView,
    AgentLeadsAPIView,
    AgentLeadDetailView,
)
from .admin_views import (
    AdminModerationStatsAPIView,
    AdminPropertyListAPIView,
    AdminPropertyDecisionAPIView,
    AdminAgentListAPIView,
    AdminAgentVerifyAPIView,
)

app_name = 'properties'

urlpatterns = [
    path('', PropertyListCreateView.as_view(), name='property_list_create'),
    path('admin/moderation/stats/', AdminModerationStatsAPIView.as_view(), name='admin_moderation_stats'),
    path('admin/moderation/properties/', AdminPropertyListAPIView.as_view(), name='admin_moderation_properties'),
    path('admin/moderation/properties/<int:pk>/decision/', AdminPropertyDecisionAPIView.as_view(), name='admin_moderation_decision'),
    path('admin/moderation/agents/', AdminAgentListAPIView.as_view(), name='admin_moderation_agents'),
    path('admin/moderation/agents/<int:pk>/verify/', AdminAgentVerifyAPIView.as_view(), name='admin_moderation_agent_verify'),
    path('inventory/', AgentInventoryAPIView.as_view(), name='property_inventory_api'),
    path('leads/', AgentLeadsAPIView.as_view(), name='agent_leads_api'),
    path('leads/<int:pk>/', AgentLeadDetailView.as_view(), name='agent_lead_detail'),
    path('<int:pk>/', PropertyDetailView.as_view(), name='property_detail'),
    path('<int:pk>/inquire/', PropertyInquiryCreateView.as_view(), name='property_inquire'),
    path('<int:pk>/images/', PropertyImageUploadView.as_view(), name='property_image_upload'),
    path('<int:pk>/images/<int:image_id>/', PropertyImageDetailView.as_view(), name='property_image_detail'),
    path('<int:pk>/nearest-amenities/', PropertyNearestAmenitiesView.as_view(), name='property_nearest_amenities'),
    path('radius-search/', PropertyRadiusSearchView.as_view(), name='property_radius_search'),
    path('polygon-search/', PropertyPolygonSearchView.as_view(), name='property_polygon_search'),
    path('bbox-search/', PropertyBoundingBoxSearchView.as_view(), name='property_bbox_search'),
]


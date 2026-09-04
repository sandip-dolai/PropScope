from django.urls import path
from .views import PropertyStatsView, AgentDashboardMetricsView

app_name = 'analytics'

urlpatterns = [
    path('stats/', PropertyStatsView.as_view(), name='property_stats'),
    path('dashboard-metrics/', AgentDashboardMetricsView.as_view(), name='dashboard_metrics'),
]

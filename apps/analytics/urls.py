from django.urls import path
from .views import PropertyStatsView

app_name = 'analytics'

urlpatterns = [
    path('stats/', PropertyStatsView.as_view(), name='property_stats'),
]

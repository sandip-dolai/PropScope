from django.urls import path
from .views import AreaListView, AreaDetailView, AreaPropertiesView

app_name = 'geography'

urlpatterns = [
    path('', AreaListView.as_view(), name='area_list'),
    path('<int:pk>/', AreaDetailView.as_view(), name='area_detail'),
    path('<int:pk>/properties/', AreaPropertiesView.as_view(), name='area_properties'),
]

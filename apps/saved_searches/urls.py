from django.urls import path
from .views import SavedSearchListCreateView, SavedSearchDetailView

app_name = 'saved_searches'

urlpatterns = [
    path('', SavedSearchListCreateView.as_view(), name='saved_search_list_create'),
    path('<int:pk>/', SavedSearchDetailView.as_view(), name='saved_search_detail'),
]

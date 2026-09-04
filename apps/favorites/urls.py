from django.urls import path
from .views import FavoriteListCreateView, FavoriteDeleteView, FavoriteIdsView

app_name = 'favorites'

urlpatterns = [
    path('', FavoriteListCreateView.as_view(), name='favorite_list_create'),
    path('ids/', FavoriteIdsView.as_view(), name='favorite_ids'),
    path('<int:property_id>/', FavoriteDeleteView.as_view(), name='favorite_delete'),
]

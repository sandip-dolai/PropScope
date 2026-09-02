from django.urls import path
from .views import FavoriteListCreateView, FavoriteDeleteView

app_name = 'favorites'

urlpatterns = [
    path('', FavoriteListCreateView.as_view(), name='favorite_list_create'),
    path('<int:property_id>/', FavoriteDeleteView.as_view(), name='favorite_delete'),
]

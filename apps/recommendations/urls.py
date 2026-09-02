from django.urls import path
from .views import RecommendationView

app_name = 'recommendations'

urlpatterns = [
    path('normal/', RecommendationView.as_view(), {'mode': 'normal'}, name='recommend_normal'),
    path('ai/', RecommendationView.as_view(), {'mode': 'ai'}, name='recommend_ai'),
    path('hybrid/', RecommendationView.as_view(), {'mode': 'hybrid'}, name='recommend_hybrid'),
]

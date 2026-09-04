from django.urls import path
from .views import (
    RegisterView,
    LoginView,
    LogoutView,
    CurrentUserView,
    DemoLoginView,
    AgentShowcaseAPIView
)

app_name = 'accounts'

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('me/', CurrentUserView.as_view(), name='current_user'),
    path('demo-login/', DemoLoginView.as_view(), name='demo_login'),
    path('agents/<int:pk>/', AgentShowcaseAPIView.as_view(), name='agent_showcase_api'),
]


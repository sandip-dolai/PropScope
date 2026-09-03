from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate, login, logout
from .serializers import RegisterSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return Response(UserSerializer(user).data)
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)


class CurrentUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class DemoLoginView(APIView):
    """
    1-Click Demo Login for quick persona evaluation.
    Protected by settings.DEMO_MODE (returns 403 when False).
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        from django.conf import settings
        from apps.accounts.models import UserRole, BuyerProfile, AgentProfile
        from django.contrib.auth import get_user_model

        if not getattr(settings, 'DEMO_MODE', False):
            return Response(
                {'error': 'Demo authentication is disabled in production environments.'},
                status=status.HTTP_403_FORBIDDEN
            )

        User = get_user_model()
        persona = request.data.get('persona', '').lower()

        if persona == 'buyer':
            user, created = User.objects.get_or_create(
                username='buyer_rahul',
                defaults={
                    'email': 'rahul.sen@example.com',
                    'first_name': 'Rahul',
                    'last_name': 'Sen',
                    'role': UserRole.BUYER
                }
            )
            if created or not hasattr(user, 'buyer_profile'):
                user.set_password('demo123')
                user.role = UserRole.BUYER
                user.save()
                BuyerProfile.objects.get_or_create(
                    user=user,
                    defaults={'preferred_city': 'Kolkata', 'preferred_budget': 10000000.00}
                )

        elif persona == 'agent':
            user = User.objects.filter(username='agent_priya').first()
            if not user:
                user = User.objects.create_user(
                    username='agent_priya',
                    email='priya@propscope.com',
                    password='agent123',
                    first_name='Priya',
                    last_name='Mukherjee',
                    role=UserRole.AGENT
                )
                AgentProfile.objects.create(
                    user=user,
                    agency_name='North Bengal & Kolkata Realtors',
                    license_number='WB-RERA-2024-5120',
                    bio='Specialist in North Kolkata & Barasat residential properties.'
                )

        elif persona == 'admin':
            user = User.objects.filter(username='admin').first()
            if not user:
                user = User.objects.create_superuser(
                    username='admin',
                    email='admin@propscope.com',
                    password='admin123',
                    role=UserRole.ADMIN
                )

        else:
            return Response(
                {'error': f"Unknown persona: '{persona}'. Valid choices: buyer, agent, admin."},
                status=status.HTTP_400_BAD_REQUEST
            )

        login(request, user)
        return Response({
            'message': f'Successfully authenticated as {user.get_full_name() or user.username}',
            'user': UserSerializer(user).data
        })


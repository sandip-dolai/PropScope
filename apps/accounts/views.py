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
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        if request.user.is_authenticated:
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


class AgentShowcaseAPIView(APIView):
    """
    Public showcase API for licensed real estate agents.
    Returns accredited agency info, WB-RERA certification, portfolio statistics,
    and all active listings represented by the agent.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        from django.contrib.auth import get_user_model
        from django.db.models import Avg, Sum
        from apps.accounts.models import UserRole
        from apps.properties.models import Property, PropertyStatus
        from apps.properties.serializers import PropertySerializer
        from .serializers import AgentShowcaseSerializer

        User = get_user_model()

        try:
            agent = User.objects.select_related('agent_profile').get(pk=pk, role=UserRole.AGENT)
        except User.DoesNotExist:
            return Response({"error": "Agent not found."}, status=status.HTTP_404_NOT_FOUND)

        active_properties = Property.objects.filter(
            agent=agent,
            status=PropertyStatus.ACTIVE
        ).order_by('-created_at')

        total_count = active_properties.count()
        total_aum = active_properties.aggregate(total=Sum('price'))['total'] or 0
        avg_price = active_properties.aggregate(avg=Avg('price'))['avg'] or 0

        submarkets = set()
        for p in active_properties:
            parts = [s.strip() for s in p.address.split(',')]
            if len(parts) >= 2:
                submarkets.add(parts[-2])
            elif parts:
                submarkets.add(parts[0])

        agent_data = AgentShowcaseSerializer(agent).data
        properties_data = PropertySerializer(active_properties, many=True).data

        return Response({
            "agent": agent_data,
            "portfolio_stats": {
                "active_listings_count": total_count,
                "total_aum_inr": float(total_aum),
                "total_aum_crores": round(float(total_aum) / 10000000, 2),
                "average_price_inr": float(avg_price),
                "average_price_lakhs": round(float(avg_price) / 100000, 2),
                "submarkets": sorted(list(submarkets))
            },
            "properties": properties_data
        })



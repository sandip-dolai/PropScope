from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth import get_user_model
from django.db.models import Sum, Count, Q
from apps.accounts.models import UserRole, AgentProfile
from apps.accounts.serializers import AdminAgentSerializer
from .models import Property, PropertyStatus
from .serializers import PropertySerializer

User = get_user_model()


class IsPlatformAdmin(permissions.BasePermission):
    """
    Permission check strictly enforcing platform administrator privileges.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_platform_admin
        )


class AdminModerationStatsAPIView(APIView):
    """
    Platform governance and market health telemetry endpoint for administrators.
    """
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        total_properties = Property.objects.count()
        pending_count = Property.objects.filter(status=PropertyStatus.PENDING_APPROVAL).count()
        active_count = Property.objects.filter(status=PropertyStatus.ACTIVE).count()
        inactive_count = Property.objects.filter(
            status__in=[PropertyStatus.INACTIVE, PropertyStatus.SOLD, PropertyStatus.RENTED]
        ).count()

        total_aum = Property.objects.filter(
            status=PropertyStatus.ACTIVE
        ).aggregate(total=Sum('price'))['total'] or 0

        total_agents = User.objects.filter(role=UserRole.AGENT).count()
        verified_agents = AgentProfile.objects.filter(is_verified=True).count()
        compliance_pct = round((verified_agents / total_agents * 100), 1) if total_agents > 0 else 0.0

        # Submarket breakdown from property addresses
        all_active = Property.objects.filter(status=PropertyStatus.ACTIVE).values_list('address', flat=True)
        submarket_map = {}
        for addr in all_active:
            parts = [s.strip() for s in addr.split(',')]
            sub = parts[-2] if len(parts) >= 2 else (parts[0] if parts else 'Kolkata Metro')
            submarket_map[sub] = submarket_map.get(sub, 0) + 1

        submarkets_sorted = [
            {"name": k, "count": v}
            for k, v in sorted(submarket_map.items(), key=lambda x: x[1], reverse=True)
        ]

        return Response({
            "total_properties": total_properties,
            "pending_properties": pending_count,
            "active_properties": active_count,
            "inactive_properties": inactive_count,
            "total_aum_inr": float(total_aum),
            "total_aum_crores": round(float(total_aum) / 10000000, 2),
            "total_agents": total_agents,
            "verified_agents": verified_agents,
            "compliance_percentage": compliance_pct,
            "submarkets": submarkets_sorted
        })


class AdminPropertyListAPIView(APIView):
    """
    Administrative moderation queue for inspecting and filtering properties across all statuses.
    """
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        qs = Property.objects.select_related('agent', 'agent__agent_profile').prefetch_related('images')

        # Status counts for pipeline tabs
        status_counts = {
            "ALL": qs.count(),
            "PENDING_APPROVAL": qs.filter(status=PropertyStatus.PENDING_APPROVAL).count(),
            "ACTIVE": qs.filter(status=PropertyStatus.ACTIVE).count(),
            "INACTIVE": qs.filter(status=PropertyStatus.INACTIVE).count(),
            "UNDER_OFFER": qs.filter(status=PropertyStatus.UNDER_OFFER).count(),
            "SOLD": qs.filter(status=PropertyStatus.SOLD).count(),
        }

        # Filter by status (default is PENDING_APPROVAL unless specified)
        status_filter = request.query_params.get('status', 'PENDING_APPROVAL').strip().upper()
        if status_filter and status_filter != 'ALL':
            qs = qs.filter(status=status_filter)

        # Search filter
        search = request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(title__icontains=search) |
                Q(address__icontains=search) |
                Q(agent__first_name__icontains=search) |
                Q(agent__last_name__icontains=search) |
                Q(agent__agent_profile__agency_name__icontains=search) |
                Q(agent__agent_profile__license_number__icontains=search)
            )

        ordering = request.query_params.get('ordering', '-created_at')
        allowed_orderings = {'-created_at', 'created_at', 'price', '-price', 'title', '-title'}
        if ordering in allowed_orderings:
            qs = qs.order_by(ordering)
        else:
            qs = qs.order_by('-created_at')

        serializer = PropertySerializer(qs, many=True)
        return Response({
            "status_counts": status_counts,
            "count": len(qs),
            "results": serializer.data
        })


class AdminPropertyDecisionAPIView(APIView):
    """
    1-Click approve or reject decision for property listings.
    """
    permission_classes = [IsPlatformAdmin]

    def post(self, request, pk):
        try:
            prop = Property.objects.select_related('agent').get(pk=pk)
        except Property.DoesNotExist:
            return Response({"error": "Property not found."}, status=status.HTTP_404_NOT_FOUND)

        action = request.data.get('action', '').strip().lower()
        if action == 'approve':
            prop.status = PropertyStatus.ACTIVE
            prop.save(update_fields=['status', 'updated_at'])
            msg = f"Listing '{prop.title}' approved and published to active market."
        elif action == 'reject':
            prop.status = PropertyStatus.INACTIVE
            prop.save(update_fields=['status', 'updated_at'])
            msg = f"Listing '{prop.title}' rejected and archived."
        else:
            return Response(
                {"error": f"Invalid action '{action}'. Valid actions are 'approve' or 'reject'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({
            "message": msg,
            "property": PropertySerializer(prop).data
        }, status=status.HTTP_200_OK)


class AdminAgentListAPIView(APIView):
    """
    List all registered agents with WB-RERA accreditation credentials.
    """
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        qs = User.objects.filter(role=UserRole.AGENT).select_related('agent_profile').prefetch_related('properties')

        search = request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(agent_profile__agency_name__icontains=search) |
                Q(agent_profile__license_number__icontains=search)
            )

        # Verification filter
        verified_filter = request.query_params.get('verified', '').strip().lower()
        if verified_filter == 'true':
            qs = qs.filter(agent_profile__is_verified=True)
        elif verified_filter == 'false':
            qs = qs.filter(Q(agent_profile__is_verified=False) | Q(agent_profile__isnull=True))

        qs = qs.order_by('-date_joined')
        serializer = AdminAgentSerializer(qs, many=True)
        return Response({
            "count": len(qs),
            "results": serializer.data
        })


class AdminAgentVerifyAPIView(APIView):
    """
    Toggle or set official WB-RERA verification accreditation status for an agent.
    """
    permission_classes = [IsPlatformAdmin]

    def post(self, request, pk):
        try:
            agent = User.objects.select_related('agent_profile').get(pk=pk, role=UserRole.AGENT)
        except User.DoesNotExist:
            return Response({"error": "Agent not found."}, status=status.HTTP_404_NOT_FOUND)

        profile = getattr(agent, 'agent_profile', None)
        if not profile:
            profile = AgentProfile.objects.create(user=agent)

        if 'is_verified' in request.data:
            profile.is_verified = bool(request.data['is_verified'])
        else:
            profile.is_verified = not profile.is_verified

        profile.save(update_fields=['is_verified'])

        status_str = "Verified WB-RERA compliant" if profile.is_verified else "Verification revoked"
        return Response({
            "message": f"Agent {agent.get_full_name() or agent.username} updated to: {status_str}.",
            "agent": AdminAgentSerializer(agent).data
        }, status=status.HTTP_200_OK)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth import get_user_model
from django.db.models import Sum, Count, Q
from apps.accounts.models import UserRole, AgentProfile
from apps.accounts.serializers import AdminAgentSerializer
from apps.properties.models import Property, PropertyStatus
from apps.properties.serializers import PropertySerializer
from apps.amenities.models import Amenity
from apps.amenities.serializers import AmenitySerializer
from apps.geography.models import Area
from apps.geography.serializers import AreaSerializer
from rest_framework import serializers

User = get_user_model()

class AdminUserSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'role_display', 'is_active', 'date_joined']


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

        # Pagination
        from rest_framework.pagination import PageNumberPagination
        paginator = PageNumberPagination()
        paginator.page_size = 10
        paginated_qs = paginator.paginate_queryset(qs, request)

        serializer = PropertySerializer(paginated_qs, many=True)
        resp = paginator.get_paginated_response(serializer.data)
        resp.data['status_counts'] = status_counts
        return resp


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


class AdminPropertyBulkDecisionAPIView(APIView):
    """
    Bulk approve or reject decision for multiple property listings.
    """
    permission_classes = [IsPlatformAdmin]

    def post(self, request):
        action = request.data.get('action', '').strip().lower()
        property_ids = request.data.get('property_ids', [])
        
        if not action or not property_ids:
            return Response({"error": "Action and property_ids are required."}, status=status.HTTP_400_BAD_REQUEST)
            
        props = Property.objects.filter(id__in=property_ids)
        count = props.count()
        
        if action == 'approve':
            props.update(status=PropertyStatus.ACTIVE)
            msg = f"Successfully approved {count} properties."
        elif action == 'reject':
            props.update(status=PropertyStatus.INACTIVE)
            msg = f"Successfully rejected {count} properties."
        else:
            return Response({"error": "Invalid action."}, status=status.HTTP_400_BAD_REQUEST)
            
        return Response({"message": msg}, status=status.HTTP_200_OK)


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


class AdminUserListAPIView(APIView):
    """List all registered users (Buyers, Agents, Admins) for moderation."""
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        qs = User.objects.all().order_by('-date_joined')
        
        # Filtering
        search = request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )
            
        role = request.query_params.get('role', '').strip()
        if role:
            qs = qs.filter(role=role)
            
        # Pagination
        from rest_framework.pagination import PageNumberPagination
        paginator = PageNumberPagination()
        paginator.page_size = 10
        paginated_qs = paginator.paginate_queryset(qs, request)
        
        serializer = AdminUserSerializer(paginated_qs, many=True)
        return paginator.get_paginated_response(serializer.data)


class AdminUserBulkActionAPIView(APIView):
    """Perform bulk actions on users."""
    permission_classes = [IsPlatformAdmin]

    def post(self, request):
        action = request.data.get('action')
        user_ids = request.data.get('user_ids', [])
        
        if not action or not user_ids:
            return Response({"error": "Action and user_ids are required."}, status=status.HTTP_400_BAD_REQUEST)
            
        users = User.objects.filter(id__in=user_ids).exclude(id=request.user.id) # Prevent self-modification in bulk
        count = users.count()
        
        if action == 'activate':
            users.update(is_active=True)
            msg = f"Successfully activated {count} users."
        elif action == 'suspend':
            users.update(is_active=False)
            msg = f"Successfully suspended {count} users."
        elif action == 'delete':
            users.delete()
            msg = f"Successfully deleted {count} users."
        else:
            return Response({"error": "Invalid action."}, status=status.HTTP_400_BAD_REQUEST)
            
        return Response({"message": msg}, status=status.HTTP_200_OK)


class AdminUserDetailAPIView(APIView):
    """Retrieve or update a user (including toggle active)."""
    permission_classes = [IsPlatformAdmin]

    def get_object(self, pk):
        try:
            return User.objects.get(pk=pk)
        except User.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound(detail="User not found.")

    def put(self, request, pk):
        user = self.get_object(pk)
        
        if 'is_active' in request.data:
            if user == request.user and not request.data['is_active']:
                return Response({"error": "You cannot suspend your own account."}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = AdminUserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": f"User '{user.username}' updated successfully.",
                "user": serializer.data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminAmenityListAPIView(APIView):
    """List all amenities or create a new one."""
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        qs = Amenity.objects.select_related('category').order_by('-created_at')
        search = request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(name__icontains=search) |
                Q(address__icontains=search) |
                Q(category__name__icontains=search)
            )
        
        # Simple pagination since amenities list can be long
        page = int(request.query_params.get('page', 1))
        page_size = 50
        start = (page - 1) * page_size
        end = start + page_size

        serializer = AmenitySerializer(qs[start:end], many=True)
        return Response({
            "count": qs.count(),
            "results": serializer.data
        })

    def post(self, request):
        serializer = AmenitySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Amenity created successfully.", "amenity": serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminAmenityDetailAPIView(APIView):
    """Retrieve, update or delete an amenity."""
    permission_classes = [IsPlatformAdmin]

    def get_object(self, pk):
        try:
            return Amenity.objects.get(pk=pk)
        except Amenity.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound(detail="Amenity not found.")

    def put(self, request, pk):
        amenity = self.get_object(pk)
        serializer = AmenitySerializer(amenity, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": f"Amenity '{amenity.name}' updated successfully.", "amenity": serializer.data}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        amenity = self.get_object(pk)
        name = amenity.name
        amenity.delete()
        return Response({"message": f"Amenity '{name}' deleted successfully."}, status=status.HTTP_200_OK)


class AdminAreaListAPIView(APIView):
    """List all neighborhood geofences."""
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        qs = Area.objects.all().order_by('-created_at')
        serializer = AreaSerializer(qs, many=True)
        return Response({
            "count": len(qs),
            "results": serializer.data
        })

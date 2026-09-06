from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Avg, Count, Min, Max, Sum, F, ExpressionWrapper, DecimalField
from apps.properties.models import Property, PropertyStatus, PropertyType
from apps.geography.models import Area
from apps.accounts.models import UserRole


def format_inr(price):
    if not price:
        return "₹0.00"
    num = float(price)
    if num >= 10000000:
        return f"₹{num / 10000000:.2f} Cr"
    elif num >= 100000:
        return f"₹{num / 100000:.2f} L"
    return f"₹{num:,.2f}"


class PropertyStatsView(APIView):
    """
    Returns platform-wide or area-specific aggregate real estate statistics.
    """
    def get(self, request):
        stats = Property.objects.filter(status=PropertyStatus.ACTIVE).aggregate(
            total_count=Count('id'),
            avg_price=Avg('price'),
            min_price=Min('price'),
            max_price=Max('price'),
            avg_area=Avg('area_sqft'),
        )
        return Response(stats)


class AgentDashboardMetricsView(APIView):
    """
    Returns executive portfolio metrics for verified Agents and Administrators.
    For Buyers, returns a personalized buyer dashboard with favorites,
    saved searches, and recommendation counts.
    Agents see their managed inventory; Admins see system-wide inventory.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        # Buyer Dashboard — return buyer-specific data instead of 403
        if user.role == UserRole.BUYER and not user.is_staff:
            return self._get_buyer_dashboard(user)

        # Queryset scoping
        if user.role == UserRole.AGENT and not user.is_staff:
            qs = Property.objects.filter(agent=user)
            scope_title = "Agent Managed Portfolio"
        else:
            qs = Property.objects.all()
            scope_title = "Metropolitan Platform Portfolio"

        total_listings = qs.count()
        active_qs = qs.filter(status=PropertyStatus.ACTIVE)
        active_count = active_qs.count()
        sold_count = qs.filter(status=PropertyStatus.SOLD).count()
        rented_count = qs.filter(status=PropertyStatus.RENTED).count()
        inactive_count = qs.filter(status__in=[PropertyStatus.INACTIVE, PropertyStatus.PENDING_APPROVAL]).count()

        # Valuation & Yield calculations
        aum_sum = active_qs.aggregate(total=Sum('price'))['total'] or 0
        avg_price = active_qs.aggregate(avg=Avg('price'))['avg'] or 0

        # Calculate average price per sqft across active inventory
        active_with_rate = active_qs.annotate(
            rate=ExpressionWrapper(F('price') / F('area_sqft'), output_field=DecimalField(max_digits=12, decimal_places=2))
        )
        avg_price_sqft = active_with_rate.aggregate(avg_rate=Avg('rate'))['avg_rate'] or 0

        # Configuration Breakdown
        bhk_breakdown = {
            "1 BHK": qs.filter(bedrooms=1).count(),
            "2 BHK": qs.filter(bedrooms=2).count(),
            "3 BHK": qs.filter(bedrooms=3).count(),
            "4+ BHK": qs.filter(bedrooms__gte=4).count(),
        }

        # Sub-Market Distribution via PostGIS ST_Within
        submarkets = []
        for area in Area.objects.all().order_by('name'):
            count = qs.filter(location__within=area.boundary).count()
            if count > 0:
                submarkets.append({
                    "id": area.id,
                    "name": area.name,
                    "city": area.city,
                    "count": count,
                })

        # Recent Asset Activity
        recent_props = []
        for prop in qs.order_by('-updated_at')[:5]:
            recent_props.append({
                "id": prop.id,
                "title": prop.title,
                "price": float(prop.price),
                "formatted_price": format_inr(prop.price),
                "status": prop.status,
                "bedrooms": prop.bedrooms,
                "area_sqft": float(prop.area_sqft),
                "address": prop.address,
                "updated_at": prop.updated_at.strftime("%b %d, %Y"),
            })

        agent_profile = {
            "name": user.get_full_name() or user.username,
            "email": user.email,
            "role": user.role,
            "agency_name": getattr(getattr(user, 'agent_profile', None), 'agency_name', 'Independent Broker'),
            "license_number": getattr(getattr(user, 'agent_profile', None), 'license_number', 'WB-RERA Verified'),
        }

        return Response({
            "scope_title": scope_title,
            "agent_profile": agent_profile,
            "metrics": {
                "total_aum": float(aum_sum),
                "formatted_aum": format_inr(aum_sum),
                "total_listings": total_listings,
                "active_count": active_count,
                "sold_count": sold_count,
                "rented_count": rented_count,
                "inactive_count": inactive_count,
                "avg_price": float(avg_price),
                "formatted_avg_price": format_inr(avg_price),
                "avg_price_sqft": round(float(avg_price_sqft), 2),
            },
            "bhk_breakdown": bhk_breakdown,
            "submarkets": submarkets,
            "recent_properties": recent_props,
        })

    def _get_buyer_dashboard(self, user):
        """Return buyer-specific dashboard metrics."""
        from apps.favorites.models import Favorite
        from apps.saved_searches.models import SavedSearch

        favorites_count = Favorite.objects.filter(user=user).count()
        saved_searches_count = SavedSearch.objects.filter(user=user).count()

        # Platform stats for buyer context
        active_properties = Property.objects.filter(status=PropertyStatus.ACTIVE)
        total_active = active_properties.count()
        avg_price = active_properties.aggregate(avg=Avg('price'))['avg'] or 0

        # Recent favorites
        recent_favorites = []
        for fav in Favorite.objects.filter(user=user).select_related('property').order_by('-created_at')[:5]:
            prop = fav.property
            recent_favorites.append({
                "id": prop.id,
                "title": prop.title,
                "price": float(prop.price),
                "formatted_price": format_inr(prop.price),
                "bedrooms": prop.bedrooms,
                "area_sqft": float(prop.area_sqft),
                "address": prop.address,
                "favorited_at": fav.created_at.strftime("%b %d, %Y"),
            })

        # Recent saved searches
        recent_searches = []
        for ss in SavedSearch.objects.filter(user=user).order_by('-created_at')[:5]:
            recent_searches.append({
                "id": ss.id,
                "name": ss.title,
                "created_at": ss.created_at.strftime("%b %d, %Y"),
            })

        return Response({
            "dashboard_type": "buyer",
            "user_profile": {
                "name": user.get_full_name() or user.username,
                "email": user.email,
                "role": user.role,
            },
            "metrics": {
                "favorites_count": favorites_count,
                "saved_searches_count": saved_searches_count,
                "total_active_properties": total_active,
                "avg_market_price": format_inr(avg_price),
            },
            "recent_favorites": recent_favorites,
            "recent_searches": recent_searches,
        })

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView


@method_decorator(ensure_csrf_cookie, name='dispatch')
class HomeView(TemplateView):
    template_name = 'home.html'


@method_decorator(ensure_csrf_cookie, name='dispatch')
class DashboardView(TemplateView):
    template_name = 'dashboard/index.html'


@method_decorator(ensure_csrf_cookie, name='dispatch')
class PropertyCreateView(TemplateView):
    template_name = 'dashboard/property_create.html'


from django.shortcuts import get_object_or_404, redirect
from django.core.exceptions import PermissionDenied
from apps.properties.models import Property


@method_decorator(ensure_csrf_cookie, name='dispatch')
class PropertyInventoryView(TemplateView):
    template_name = 'dashboard/inventory.html'


@method_decorator(ensure_csrf_cookie, name='dispatch')
class PropertyEditView(TemplateView):
    template_name = 'dashboard/property_edit.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not (request.user.is_agent or request.user.is_platform_admin):
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = kwargs.get('pk')
        prop = get_object_or_404(Property.objects.select_related('agent').prefetch_related('images'), pk=pk)
        user = self.request.user
        if not (user.is_platform_admin or prop.agent == user):
            raise PermissionDenied("You do not have permission to edit this listing.")
        context['property'] = prop
        return context


@method_decorator(ensure_csrf_cookie, name='dispatch')
class PropertyLeadsView(TemplateView):
    template_name = 'dashboard/leads.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not (request.user.is_agent or request.user.is_platform_admin):
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)


@method_decorator(ensure_csrf_cookie, name='dispatch')
class AgentShowcaseView(TemplateView):
    template_name = 'agents/showcase.html'

    def get_context_data(self, **kwargs):
        from django.contrib.auth import get_user_model
        from django.db.models import Avg, Sum
        from apps.accounts.models import UserRole
        from apps.properties.models import Property, PropertyStatus

        context = super().get_context_data(**kwargs)
        pk = kwargs.get('pk')
        User = get_user_model()
        agent = get_object_or_404(User.objects.select_related('agent_profile'), pk=pk, role=UserRole.AGENT)

        active_properties = Property.objects.filter(
            agent=agent,
            status=PropertyStatus.ACTIVE
        ).prefetch_related('images').order_by('-created_at')

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

        context['agent'] = agent
        context['properties'] = active_properties
        context['portfolio_stats'] = {
            'active_listings_count': total_count,
            'total_aum_crores': round(float(total_aum) / 10000000, 2),
            'average_price_lakhs': round(float(avg_price) / 100000, 2),
            'submarkets': sorted(list(submarkets))
        }
        return context


class AdminBaseView(TemplateView):
    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, request, *args, **kwargs):
        from django.core.exceptions import PermissionDenied
        if not request.user.is_authenticated or not request.user.is_platform_admin:
            raise PermissionDenied("Platform administrator access required.")
        return super().dispatch(request, *args, **kwargs)

class AdminOverviewView(AdminBaseView):
    template_name = 'dashboard/admin_overview.html'

class AdminQueueView(AdminBaseView):
    template_name = 'dashboard/admin_queue.html'

class AdminAgentsView(AdminBaseView):
    template_name = 'dashboard/admin_agents.html'

class AdminUsersView(AdminBaseView):
    template_name = 'dashboard/admin_users.html'

class AdminAmenitiesView(AdminBaseView):
    template_name = 'dashboard/admin_amenities.html'

class AdminAreasView(AdminBaseView):
    template_name = 'dashboard/admin_areas.html'


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', HomeView.as_view(), name='home'),
    path('agents/<int:pk>/', AgentShowcaseView.as_view(), name='agent_showcase'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('dashboard/admin/', AdminOverviewView.as_view(), name='admin_overview'),
    path('dashboard/admin/queue/', AdminQueueView.as_view(), name='admin_queue'),
    path('dashboard/admin/agents/', AdminAgentsView.as_view(), name='admin_agents'),
    path('dashboard/admin/users/', AdminUsersView.as_view(), name='admin_users'),
    path('dashboard/admin/amenities/', AdminAmenitiesView.as_view(), name='admin_amenities'),
    path('dashboard/admin/areas/', AdminAreasView.as_view(), name='admin_areas'),
    path('dashboard/inventory/', PropertyInventoryView.as_view(), name='property_inventory'),
    path('dashboard/leads/', PropertyLeadsView.as_view(), name='property_leads'),
    path('dashboard/create/', PropertyCreateView.as_view(), name='property_create'),
    path('dashboard/properties/<int:pk>/edit/', PropertyEditView.as_view(), name='property_edit'),
    
    # API Schema and Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/docs/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # API v1 routes
    path('api/v1/auth/', include('apps.accounts.urls')),
    path('api/v1/properties/', include('apps.properties.urls')),
    path('api/v1/areas/', include('apps.geography.urls')),
    path('api/v1/amenities/', include('apps.amenities.urls')),
    path('api/v1/recommendations/', include('apps.recommendations.urls')),
    path('api/v1/analytics/', include('apps.analytics.urls')),
    path('api/v1/favorites/', include('apps.favorites.urls')),
    path('api/v1/saved-searches/', include('apps.saved_searches.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

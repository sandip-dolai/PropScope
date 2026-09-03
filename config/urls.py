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


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', HomeView.as_view(), name='home'),
    
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

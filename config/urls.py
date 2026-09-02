from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    
    # API v1 routes
    path('api/v1/auth/', include('apps.accounts.urls')),
    path('api/v1/properties/', include('apps.properties.urls')),
    path('api/v1/amenities/', include('apps.amenities.urls')),
    path('api/v1/recommendations/', include('apps.recommendations.urls')),
    path('api/v1/analytics/', include('apps.analytics.urls')),
    path('api/v1/favorites/', include('apps.favorites.urls')),
    path('api/v1/saved-searches/', include('apps.saved_searches.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

from django.contrib.gis import admin
from .models import Area


@admin.register(Area)
class AreaAdmin(admin.GISModelAdmin):
    list_display = ('name', 'city', 'created_at')
    search_fields = ('name', 'city')

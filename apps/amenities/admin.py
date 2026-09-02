from django.contrib.gis import admin
from .models import Amenity, AmenityCategory


@admin.register(AmenityCategory)
class AmenityCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon')


@admin.register(Amenity)
class AmenityAdmin(admin.GISModelAdmin):
    list_display = ('name', 'category', 'address', 'created_at')
    list_filter = ('category',)
    search_fields = ('name', 'address')

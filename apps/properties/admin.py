from django.contrib.gis import admin
from .models import Property, PropertyImage


class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 1


@admin.register(Property)
class PropertyAdmin(admin.GISModelAdmin):
    list_display = ('title', 'price', 'bedrooms', 'property_type', 'status', 'agent', 'created_at')
    list_filter = ('property_type', 'status', 'bedrooms')
    search_fields = ('title', 'address', 'description')
    inlines = [PropertyImageInline]


@admin.register(PropertyImage)
class PropertyImageAdmin(admin.ModelAdmin):
    list_display = ('property', 'is_primary', 'created_at')

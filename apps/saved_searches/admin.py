from django.contrib import admin
from .models import SavedSearch


@admin.register(SavedSearch)
class SavedSearchAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'created_at')
    search_fields = ('user__username', 'title')

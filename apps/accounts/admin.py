from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, BuyerProfile, AgentProfile


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ('PropScope Role & Info', {'fields': ('role', 'phone_number')}),
    )
    list_display = ('username', 'email', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')


@admin.register(BuyerProfile)
class BuyerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'preferred_budget', 'preferred_city')


@admin.register(AgentProfile)
class AgentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'agency_name', 'license_number')

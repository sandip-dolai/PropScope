from django.contrib.auth.models import AbstractUser
from django.db import models


class UserRole(models.TextChoices):
    BUYER = "BUYER", "Buyer"
    AGENT = "AGENT", "Agent"
    ADMIN = "ADMIN", "Admin"


class User(AbstractUser):
    role = models.CharField(
        max_length=10,
        choices=UserRole.choices,
        default=UserRole.BUYER
    )
    phone_number = models.CharField(max_length=20, blank=True, null=True)

    @property
    def is_buyer(self):
        return self.role == UserRole.BUYER

    @property
    def is_agent(self):
        return self.role == UserRole.AGENT

    @property
    def is_platform_admin(self):
        return self.role == UserRole.ADMIN or self.is_superuser


class BuyerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='buyer_profile')
    preferred_budget = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    preferred_city = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"BuyerProfile: {self.user.username}"


class AgentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='agent_profile')
    agency_name = models.CharField(max_length=150, blank=True, null=True)
    license_number = models.CharField(max_length=100, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"AgentProfile: {self.user.username} ({self.agency_name or 'Independent'})"

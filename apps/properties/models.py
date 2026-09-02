from django.conf import settings
from django.db import models
from django.contrib.gis.db import models as gis_models


class PropertyType(models.TextChoices):
    APARTMENT = "APARTMENT", "Apartment"
    VILLA = "VILLA", "Villa"
    HOUSE = "HOUSE", "Independent House"
    PLOT = "PLOT", "Plot / Land"
    COMMERCIAL = "COMMERCIAL", "Commercial"
    OFFICE = "OFFICE", "Office Space"


class PropertyStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    SOLD = "SOLD", "Sold"
    RENTED = "RENTED", "Rented"
    INACTIVE = "INACTIVE", "Inactive"
    PENDING_APPROVAL = "PENDING_APPROVAL", "Pending Approval"


class Property(models.Model):
    agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='properties'
    )
    title = models.CharField(max_length=255)
    description = models.TextField()

    property_type = models.CharField(
        max_length=20,
        choices=PropertyType.choices,
        default=PropertyType.APARTMENT
    )
    status = models.CharField(
        max_length=20,
        choices=PropertyStatus.choices,
        default=PropertyStatus.ACTIVE
    )

    price = models.DecimalField(max_digits=14, decimal_places=2)
    bedrooms = models.PositiveSmallIntegerField(default=1)
    bathrooms = models.DecimalField(max_digits=4, decimal_places=1, default=1.0)
    area_sqft = models.DecimalField(max_digits=10, decimal_places=2)

    address = models.TextField()

    # PostGIS Point (Longitude, Latitude) in WGS 84 (SRID 4326)
    location = gis_models.PointField(
        srid=4326,
        geography=True,
        spatial_index=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Properties"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['price']),
            models.Index(fields=['bedrooms']),
            models.Index(fields=['property_type']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.title} - ₹{self.price:,}"

    @property
    def price_per_sqft(self):
        if self.area_sqft and self.area_sqft > 0:
            return round(self.price / self.area_sqft, 2)
        return None

    @property
    def latitude(self):
        return self.location.y if self.location else None

    @property
    def longitude(self):
        return self.location.x if self.location else None


class PropertyImage(models.Model):
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(upload_to='property_images/')
    caption = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.property.title}"

from django.db import models
from django.contrib.gis.db import models as gis_models


class AmenityCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Lucide/Tailwind icon name")

    class Meta:
        verbose_name_plural = "Amenity Categories"

    def __str__(self):
        return self.name


class Amenity(models.Model):
    category = models.ForeignKey(
        AmenityCategory,
        on_delete=models.PROTECT,
        related_name='amenities'
    )
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=255, blank=True)
    
    # PostGIS Point (Longitude, Latitude) in WGS 84
    location = gis_models.PointField(
        srid=4326,
        geography=True,
        spatial_index=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Amenities"

    def __str__(self):
        return f"{self.name} ({self.category.name})"

    @property
    def latitude(self):
        return self.location.y if self.location else None

    @property
    def longitude(self):
        return self.location.x if self.location else None

from django.db import models
from django.contrib.gis.db import models as gis_models


class Area(models.Model):
    name = models.CharField(max_length=150, unique=True)
    city = models.CharField(max_length=100, default='Default City')
    description = models.TextField(blank=True)

    # PostGIS MultiPolygon for neighborhood, locality, or administrative boundary
    boundary = gis_models.MultiPolygonField(
        srid=4326,
        spatial_index=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Areas / Neighborhoods"

    def __str__(self):
        return f"{self.name} ({self.city})"

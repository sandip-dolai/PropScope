from django.contrib.gis.db.models.functions import Distance
from .models import Amenity, AmenityCategory
from .scoring import AmenityProximityScorer


class AmenitySpatialService:
    """
    Handles PostGIS nearest-neighbor (KNN) and spatial distance calculations
    between properties and amenities.
    """

    @staticmethod
    def get_nearest_amenities_for_point(point, enrich_with_scores=True):
        """
        Given a GEOS Point (SRID 4326), finds the closest amenity in each category
        using PostGIS Distance annotation and spatial ordering.
        Optionally enriches results with normalized proximity scores (0-100) and labels.
        """
        categories = AmenityCategory.objects.all()
        nearest_results = []

        for category in categories:
            nearest_amenity = (
                Amenity.objects.filter(category=category)
                .annotate(distance=Distance('location', point))
                .order_by('distance')
                .first()
            )

            if nearest_amenity and hasattr(nearest_amenity, 'distance'):
                dist_km = round(nearest_amenity.distance.km, 2)
                dist_m = round(nearest_amenity.distance.m, 1)

                nearest_results.append({
                    "category_id": category.id,
                    "category_name": category.name,
                    "category_icon": category.icon,
                    "amenity_id": nearest_amenity.id,
                    "amenity_name": nearest_amenity.name,
                    "address": nearest_amenity.address,
                    "distance_km": dist_km,
                    "distance_m": dist_m,
                    "lat": nearest_amenity.latitude,
                    "lng": nearest_amenity.longitude,
                })

        if enrich_with_scores:
            scorer = AmenityProximityScorer()
            nearest_results = scorer.enrich_nearest_amenities(nearest_results)

        return nearest_results

    @classmethod
    def get_nearest_amenities_for_property(cls, property_obj, enrich_with_scores=True):
        """
        Finds the closest amenity per category for a given Property instance.
        """
        nearest_amenities = cls.get_nearest_amenities_for_point(
            property_obj.location,
            enrich_with_scores=enrich_with_scores
        )
        return {
            "property_id": property_obj.id,
            "property_title": property_obj.title,
            "property_location": {
                "lat": property_obj.latitude,
                "lng": property_obj.longitude
            },
            "nearest_amenities": nearest_amenities
        }


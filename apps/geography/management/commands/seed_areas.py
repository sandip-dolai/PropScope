from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Polygon, MultiPolygon
from apps.geography.models import Area


class Command(BaseCommand):
    help = "Seed database with major neighborhood MultiPolygon boundaries (Salt Lake, New Town, Dum Dum, Barasat)."

    def handle(self, *args, **options):
        self.stdout.write("Seeding neighborhood Area MultiPolygon boundaries...")

        areas_data = [
            {
                "name": "Salt Lake (Bidhannagar)",
                "city": "Kolkata",
                "description": "Planned satellite township known for IT hubs, green parks, and serene residential sectors I through V.",
                "coords": [
                    (88.398, 22.568),
                    (88.435, 22.568),
                    (88.442, 22.585),
                    (88.432, 22.596),
                    (88.405, 22.595),
                    (88.398, 22.580),
                    (88.398, 22.568),
                ]
            },
            {
                "name": "New Town (Rajarhat)",
                "city": "Kolkata",
                "description": "Fastest growing smart township with premier IT campuses, gated luxury condominiums, and wide arterial roads.",
                "coords": [
                    (88.435, 22.570),
                    (88.485, 22.570),
                    (88.490, 22.620),
                    (88.455, 22.625),
                    (88.435, 22.600),
                    (88.435, 22.570),
                ]
            },
            {
                "name": "Dum Dum & Nagerbazar",
                "city": "Kolkata",
                "description": "Historic vibrant transit hub with major Metro and railway junction, bustling markets, and excellent connectivity.",
                "coords": [
                    (88.385, 22.605),
                    (88.428, 22.605),
                    (88.430, 22.640),
                    (88.390, 22.640),
                    (88.385, 22.605),
                ]
            },
            {
                "name": "Barasat",
                "city": "North 24 Parganas",
                "description": "District administrative headquarters with railway connectivity, district healthcare centers, and budget-friendly residential colonies.",
                "coords": [
                    (88.465, 22.708),
                    (88.505, 22.708),
                    (88.505, 22.740),
                    (88.465, 22.740),
                    (88.465, 22.708),
                ]
            },
        ]

        created_count = 0
        for data in areas_data:
            poly = Polygon(data["coords"], srid=4326)
            multi_poly = MultiPolygon([poly], srid=4326)

            area, created = Area.objects.update_or_create(
                name=data["name"],
                defaults={
                    "city": data["city"],
                    "description": data["description"],
                    "boundary": multi_poly,
                }
            )
            if created:
                created_count += 1
            self.stdout.write(self.style.SUCCESS(f"Area saved: {area.name} (city: {area.city})"))

        self.stdout.write(self.style.SUCCESS(f"Successfully configured {len(areas_data)} neighborhood boundaries!"))

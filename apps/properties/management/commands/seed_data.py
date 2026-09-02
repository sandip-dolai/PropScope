from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from apps.accounts.models import UserRole, AgentProfile
from apps.properties.models import Property, PropertyType, PropertyStatus
from apps.amenities.models import AmenityCategory, Amenity

User = get_user_model()


class Command(BaseCommand):
    help = "Seed database with initial superuser, agent, amenity categories, amenities, and properties."

    def handle(self, *args, **options):
        self.stdout.write("Seeding database...")

        # 1. Admin Superuser
        admin_user, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@propscope.com",
                "role": UserRole.ADMIN,
                "is_staff": True,
                "is_superuser": True
            }
        )
        if created:
            admin_user.set_password("admin123")
            admin_user.save()
            self.stdout.write(self.style.SUCCESS("Created admin user (admin / admin123)"))

        # 2. Agent User
        agent_user, created = User.objects.get_or_create(
            username="agent_rohit",
            defaults={
                "email": "rohit@propscope.com",
                "first_name": "Rohit",
                "last_name": "Sharma",
                "role": UserRole.AGENT,
                "phone_number": "+91 98765 43210"
            }
        )
        if created:
            agent_user.set_password("agent123")
            agent_user.save()
            AgentProfile.objects.create(
                user=agent_user,
                agency_name="Skyline Realty Kolkata",
                license_number="WB-RERA-2024-8841",
                bio="Premier real estate consultant specializing in Salt Lake and New Town."
            )
            self.stdout.write(self.style.SUCCESS("Created agent user (agent_rohit / agent123)"))

        # 3. Amenity Categories
        categories_data = [
            ("Metro Station", "train"),
            ("Hospital", "cross"),
            ("School", "school"),
            ("Shopping Mall", "shopping-bag"),
            ("Park", "trees"),
        ]
        category_map = {}
        for cat_name, icon in categories_data:
            cat, _ = AmenityCategory.objects.get_or_create(name=cat_name, defaults={"icon": icon})
            category_map[cat_name] = cat

        # 4. Amenities with real PostGIS coordinates
        amenities_data = [
            ("Salt Lake Sector V Metro Station", "Metro Station", 22.5804, 88.4326, "Sector V, Salt Lake"),
            ("Karunamoyee Metro Station", "Metro Station", 22.5867, 88.4208, "Karunamoyee, Salt Lake"),
            ("Apollo Multispeciality Hospital", "Hospital", 22.5714, 88.4045, "Canal Circular Rd, Kadapara"),
            ("AMRI Hospital Salt Lake", "Hospital", 22.5855, 88.4118, "JC Block, Sector III, Salt Lake"),
            ("City Centre 1 Mall", "Shopping Mall", 22.5898, 88.4082, "DC Block, Sector 1, Salt Lake"),
            ("Central Park Salt Lake", "Park", 22.5910, 88.4180, "Central Park, Bidhannagar"),
            ("DPS Megacity School", "School", 22.6105, 88.4682, "Action Area II, New Town"),
        ]
        for name, cat_name, lat, lng, addr in amenities_data:
            Amenity.objects.get_or_create(
                name=name,
                defaults={
                    "category": category_map[cat_name],
                    "address": addr,
                    "location": Point(lng, lat, srid=4326)
                }
            )
        self.stdout.write(self.style.SUCCESS(f"Created {len(amenities_data)} amenities"))

        # 5. Properties with real PostGIS coordinates
        properties_data = [
            {
                "title": "Luxury 3BHK Skyline Residency",
                "description": "Modern high-rise apartment with panoramic city views, modular kitchen, and clubhouse access. 5 minutes from Sector V tech hub.",
                "property_type": PropertyType.APARTMENT,
                "price": 7800000.00,
                "bedrooms": 3,
                "bathrooms": 2,
                "area_sqft": 1450.00,
                "address": "Block EP, Sector V, Salt Lake, Kolkata 700091",
                "lat": 22.5840,
                "lng": 88.4250,
            },
            {
                "title": "Eco-Greens Premium 4BHK Villa",
                "description": "Spacious independent duplex villa featuring private garden, 2-car garage, solar backup, and 24/7 security.",
                "property_type": PropertyType.VILLA,
                "price": 18500000.00,
                "bedrooms": 4,
                "bathrooms": 4,
                "area_sqft": 2800.00,
                "address": "Action Area I, New Town, Kolkata 700156",
                "lat": 22.5960,
                "lng": 88.4410,
            },
            {
                "title": "Urban Edge 2BHK Apartment",
                "description": "Well-ventilated, vastu-compliant 2BHK apartment ideal for young professionals or small families. Walking distance to market.",
                "property_type": PropertyType.APARTMENT,
                "price": 5200000.00,
                "bedrooms": 2,
                "bathrooms": 2,
                "area_sqft": 980.00,
                "address": "Sector II, Salt Lake, Kolkata 700091",
                "lat": 22.5790,
                "lng": 88.4160,
            },
            {
                "title": "Metro View 3BHK Residence",
                "description": "Premium flat situated right opposite the Metro station. Features 3 balconies, high-speed elevators, and gym.",
                "property_type": PropertyType.APARTMENT,
                "price": 8200000.00,
                "bedrooms": 3,
                "bathrooms": 3,
                "area_sqft": 1600.00,
                "address": "Near Karunamoyee Central, Sector II, Salt Lake, Kolkata 700091",
                "lat": 22.5815,
                "lng": 88.4310,
            },
            {
                "title": "Lakefront Executive 3BHK Flat",
                "description": "Stunning lake view apartment in a gated society with swimming pool, badminton court, and supermarket within premises.",
                "property_type": PropertyType.APARTMENT,
                "price": 7450000.00,
                "bedrooms": 3,
                "bathrooms": 2,
                "area_sqft": 1380.00,
                "address": "Sector III, Near Subhash Sarovar, Kolkata 700098",
                "lat": 22.5890,
                "lng": 88.4220,
            },
        ]

        for pdata in properties_data:
            lat = pdata.pop("lat")
            lng = pdata.pop("lng")
            Property.objects.get_or_create(
                title=pdata["title"],
                defaults={
                    **pdata,
                    "agent": agent_user,
                    "location": Point(lng, lat, srid=4326),
                    "status": PropertyStatus.ACTIVE
                }
            )
        self.stdout.write(self.style.SUCCESS(f"Created {len(properties_data)} properties"))
        self.stdout.write(self.style.SUCCESS("Database seeding completed successfully!"))

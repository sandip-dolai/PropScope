from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from apps.accounts.models import UserRole, AgentProfile
from apps.properties.models import Property, PropertyType, PropertyStatus
from apps.amenities.models import AmenityCategory, Amenity

User = get_user_model()


class Command(BaseCommand):
    help = "Seed database with 50 realistic properties and key amenities across North Kolkata up to Barasat."

    def handle(self, *args, **options):
        self.stdout.write("Seeding North Kolkata to Barasat properties & amenities...")

        # 1. Ensure Agent user exists
        agent, _ = User.objects.get_or_create(
            username="agent_priya",
            defaults={
                "email": "priya@propscope.com",
                "first_name": "Priya",
                "last_name": "Mukherjee",
                "role": UserRole.AGENT,
                "phone_number": "+91 98301 23456"
            }
        )
        if not hasattr(agent, 'agent_profile'):
            agent.set_password("agent123")
            agent.save()
            AgentProfile.objects.create(
                user=agent,
                agency_name="North Bengal & Kolkata Realtors",
                license_number="WB-RERA-2024-5120",
                bio="Specialist in North Kolkata, BT Road, Jessore Road, and Barasat residential properties."
            )

        # 2. Amenity Categories
        cat_metro, _ = AmenityCategory.objects.get_or_create(name="Metro Station", defaults={"icon": "train"})
        cat_hosp, _ = AmenityCategory.objects.get_or_create(name="Hospital", defaults={"icon": "cross"})
        cat_school, _ = AmenityCategory.objects.get_or_create(name="School", defaults={"icon": "school"})
        cat_mall, _ = AmenityCategory.objects.get_or_create(name="Shopping Mall", defaults={"icon": "shopping-bag"})
        cat_park, _ = AmenityCategory.objects.get_or_create(name="Park", defaults={"icon": "trees"})

        # 3. North Kolkata to Barasat Amenities
        amenities_data = [
            # Metro / Railway Stations
            ("Shyambazar Metro Station", cat_metro, 22.6042, 88.3725, "5-Point Crossing, Shyambazar"),
            ("Belgachia Metro Station", cat_metro, 22.6075, 88.3888, "Belgachia, North Kolkata"),
            ("Dum Dum Metro & Junction", cat_metro, 22.6218, 88.3934, "Dum Dum Station Road"),
            ("Baranagar Metro Station", cat_metro, 22.6481, 88.3755, "BT Road, Baranagar"),
            ("Dakshineswar Metro Station", cat_metro, 22.6548, 88.3639, "Dakshineswar, Kolkata"),
            ("Kolkata Airport Metro Station", cat_metro, 22.6495, 88.4442, "NSCB International Airport"),
            ("Madhyamgram Railway Station", cat_metro, 22.6985, 88.4688, "Station Road, Madhyamgram"),
            ("Barasat Junction Railway Station", cat_metro, 22.7215, 88.4845, "Station Road, Barasat"),

            # Hospitals
            ("R. G. Kar Medical College & Hospital", cat_hosp, 22.6045, 88.3805, "1 Khudiram Bose Sarani, Belgachia"),
            ("ILS Hospitals Dum Dum", cat_hosp, 22.6250, 88.4215, "1 Mall Road, Nagerbazar"),
            ("Zenith Super Specialist Hospital", cat_hosp, 22.6510, 88.3840, "Feeder Road, Belgharia"),
            ("Narayana Multispeciality Hospital Barasat", cat_hosp, 22.7160, 88.4870, "Jessore Road, Champadali, Barasat"),
            ("Barasat District Hospital", cat_hosp, 22.7250, 88.4810, "Banamalipur, Barasat"),
            ("Disha Eye Hospital Barrackpore", cat_hosp, 22.6820, 88.4550, "Jessore Road, Ganganagar"),

            # Schools
            ("Scottish Church Collegiate School", cat_school, 22.5980, 88.3690, "Bidhan Sarani, Shyambazar"),
            ("Auxilium Convent School Dum Dum", cat_school, 22.6280, 88.4230, "Dum Dum Cantonment"),
            ("Adamas International School", cat_school, 22.6680, 88.4050, "Belgharia Expressway"),
            ("Julien Day School Ganganagar", cat_school, 22.6880, 88.4610, "Jessore Road, Madhyamgram"),
            ("Barasat Government High School", cat_school, 22.7220, 88.4830, "Barrackpore Road, Barasat"),

            # Shopping Malls & Markets
            ("Diamond Plaza Mall", cat_mall, 22.6235, 88.4190, "Jessore Road, Nagerbazar"),
            ("City Centre 2 Chinar Park", cat_mall, 22.6285, 88.4550, "Action Area II, Rajarhat"),
            ("Star Mall Madhyamgram", cat_mall, 22.6960, 88.4710, "Jessore Road, Madhyamgram"),
            ("Barasat Duckbungalow Market", cat_mall, 22.7240, 88.4850, "Duckbungalow More, Barasat"),

            # Parks
            ("Bagbazar Ghat Promenade & Park", cat_park, 22.6030, 88.3640, "Ganga Ghat, Bagbazar"),
            ("Dum Dum Park Bharat Chakra", cat_park, 22.6080, 88.4120, "Dum Dum Park, Lake View"),
            ("Madhyamgram Kuthi Park", cat_park, 22.7020, 88.4730, "East Kodalia, Madhyamgram"),
            ("Barasat Stadium & Park Ground", cat_park, 22.7280, 88.4910, "Pioneer, Barasat"),
        ]

        amenities_created = 0
        for name, category, lat, lng, addr in amenities_data:
            _, created = Amenity.objects.get_or_create(
                name=name,
                defaults={
                    "category": category,
                    "address": addr,
                    "location": Point(lng, lat, srid=4326)
                }
            )
            if created:
                amenities_created += 1

        self.stdout.write(self.style.SUCCESS(f"Added {amenities_created} new amenities along North Kolkata - Barasat corridor"))

        # 4. 50 Properties from Shyambazar/North Kolkata upto Barasat
        properties_catalog = [
            # 1-5: Shyambazar & Bagbazar
            ("Heritage 3BHK Haven Shyambazar", "Stately colonial high-ceiling 3BHK flat near 5-point crossing.", PropertyType.APARTMENT, 8400000.00, 3, 2, 1420.0, "Near Shyambazar 5-Point, Kolkata 700004", 22.6038, 88.3718),
            ("Bagbazar Riverview 2BHK Apartment", "Serene Ganga view modern apartment with rooftop terrace.", PropertyType.APARTMENT, 5800000.00, 2, 2, 980.0, "Bagbazar Street, North Kolkata 700003", 22.6025, 88.3650),
            ("Shyampukur Executive 3BHK Flat", "Spacious 3BHK with covered car parking and lift.", PropertyType.APARTMENT, 7600000.00, 3, 2, 1310.0, "Shyampukur Street, Kolkata 700004", 22.6010, 88.3740),
            ("Sovabazar Traditional 4BHK Mansion House", "Historic independent ancestral house with courtyard.", PropertyType.HOUSE, 14500000.00, 4, 3, 2350.0, "Sovabazar, North Kolkata 700005", 22.5975, 88.3680),
            ("Hatibagan Market Central 2BHK", "Convenient apartment right by the famous Hatibagan shopping corridor.", PropertyType.APARTMENT, 4950000.00, 2, 1, 875.0, "Bidhan Sarani, Hatibagan 700004", 22.5995, 88.3732),

            # 6-9: Cossipore & Sinthee
            ("Cossipore Riverside 3BHK Residency", "Contemporary gated complex overlooking the Hooghly river.", PropertyType.APARTMENT, 6900000.00, 3, 2, 1250.0, "Kashipur Road, Cossipore, Kolkata 700002", 22.6180, 88.3685),
            ("Sinthee More 2BHK Cozy Home", "Ready-to-move-in sunny 2BHK flat near BT Road junction.", PropertyType.APARTMENT, 4200000.00, 2, 2, 850.0, "Sinthee More, BT Road, Kolkata 700050", 22.6280, 88.3760),
            ("Sinthee Greenwoods 3BHK Flat", "Peaceful society with children's park and 24-hr security.", PropertyType.APARTMENT, 6250000.00, 3, 2, 1180.0, "Kalicharan Ghosh Road, Sinthee 700050", 22.6295, 88.3820),
            ("Cossipore Gun Foundry Road 2BHK", "Affordable 2BHK with low maintenance near metro connectivity.", PropertyType.APARTMENT, 3800000.00, 2, 1, 790.0, "Gun Foundry Road, Cossipore 700002", 22.6140, 88.3720),

            # 10-15: Dum Dum Junction & Cantonment
            ("Dum Dum Junction Premier 3BHK", "Walking distance to Dum Dum Station & Metro interchange.", PropertyType.APARTMENT, 6800000.00, 3, 2, 1220.0, "Subhash Nagar, Dum Dum 700028", 22.6230, 88.3950),
            ("Dum Dum Cantonment 2BHK Sunlit Flat", "Modern 2BHK in gated community near railway station.", PropertyType.APARTMENT, 3950000.00, 2, 2, 860.0, "Cantonment Station Road, Dum Dum 700065", 22.6360, 88.4110),
            ("Motijheel Greens 3BHK Apartment", "Spacious flat near Motijheel College with scenic garden views.", PropertyType.APARTMENT, 5900000.00, 3, 2, 1150.0, "Motijheel, Dum Dum, Kolkata 700074", 22.6275, 88.4020),
            ("Dum Dum Park Lakefront 3BHK Flat", "Prestigious address overlooking the lake with dedicated parking.", PropertyType.APARTMENT, 7800000.00, 3, 2, 1380.0, "Tank 3, Dum Dum Park, Kolkata 700055", 22.6110, 88.4100),
            ("Dum Dum Park Boutique 2BHK", "Designer interior flat in tranquil Dum Dum Park enclave.", PropertyType.APARTMENT, 5400000.00, 2, 2, 940.0, "Block A, Dum Dum Park 700055", 22.6095, 88.4140),
            ("Gorabazar Independent Duplex House", "Exclusive 3BHK independent home with private rooftop.", PropertyType.HOUSE, 8900000.00, 3, 3, 1750.0, "Gorabazar, Dum Dum Cantonment 700028", 22.6310, 88.4060),

            # 16-20: Nagerbazar & Bangur
            ("Diamond City North Luxury 3BHK", "Flagship complex living with swimming pool, gym, and clubhouse.", PropertyType.APARTMENT, 8600000.00, 3, 3, 1510.0, "Jessore Road, Nagerbazar, Kolkata 700055", 22.6225, 88.4205),
            ("Nagerbazar Central 2BHK Flat", "Seconds from shopping mall, cinema, and market complex.", PropertyType.APARTMENT, 4600000.00, 2, 2, 910.0, "Ramgarh, Nagerbazar, Kolkata 700028", 22.6255, 88.4170),
            ("Bangur Avenue Prime 3BHK Residency", "Upscale neighborhood flat with marble flooring and lift.", PropertyType.APARTMENT, 9200000.00, 3, 3, 1550.0, "Block B, Bangur Avenue, Kolkata 700055", 22.6060, 88.4080),
            ("Bangur Avenue Compact 2BHK", "High-demand rental property in peaceful Bangur locality.", PropertyType.APARTMENT, 5300000.00, 2, 1, 880.0, "Block C, Bangur Avenue, Kolkata 700055", 22.6045, 88.4060),
            ("Jessore Road Commercial Suite", "High-visibility office space on main Jessore Road corridor.", PropertyType.OFFICE, 7500000.00, 1, 1, 950.0, "Near ILS Hospital, Nagerbazar 700074", 22.6240, 88.4220),

            # 21-25: Baranagar & Belgharia (BT Road Corridor)
            ("Baranagar Metro Enclave 2BHK", "Steps away from Baranagar Metro station on BT Road.", PropertyType.APARTMENT, 4700000.00, 2, 2, 920.0, "Near Baranagar Metro, BT Road 700036", 22.6465, 88.3740),
            ("Belgharia Zenith View 3BHK Flat", "Spacious airy 3BHK flat near railway station and hospital.", PropertyType.APARTMENT, 5600000.00, 3, 2, 1200.0, "Feeder Road, Belgharia, Kolkata 700056", 22.6520, 88.3855),
            ("BT Road Skyline 3BHK Highrise", "20th-floor panoramic apartment with luxury lifestyle amenities.", PropertyType.APARTMENT, 8100000.00, 3, 2, 1425.0, "BT Road, Rathtala, Belgharia 700056", 22.6580, 88.3810),
            ("Belgharia Expressway 4BHK Villa", "Private gated villa with double car garage and personal garden.", PropertyType.VILLA, 13800000.00, 4, 4, 2400.0, "Expressway Junction, Belgharia 700056", 22.6650, 88.3980),
            ("Dunlop Bridge Junction 2BHK Flat", "Prime commuting hub flat with instant connectivity to howrah & airport.", PropertyType.APARTMENT, 4400000.00, 2, 1, 860.0, "Dunlop, Kolkata 700108", 22.6530, 88.3710),

            # 26-31: Airport, Birati & Michael Nagar
            ("Airport Gateway 3BHK Residence", "Ultra-convenient flat 5 minutes from Terminal 2 gates.", PropertyType.APARTMENT, 6750000.00, 3, 2, 1290.0, "VIP Road Extension, Airport Gate 1 700052", 22.6440, 88.4380),
            ("Birati Railway Station 2BHK", "Budget-friendly family home near market and local station.", PropertyType.APARTMENT, 3450000.00, 2, 1, 820.0, "Station Road, Birati, Kolkata 700051", 22.6630, 88.4410),
            ("Michael Nagar Greenwoods 3BHK", "Gated apartment complex with community hall and power backup.", PropertyType.APARTMENT, 4900000.00, 3, 2, 1140.0, "Jessore Road, Michael Nagar 700133", 22.6680, 88.4480),
            ("Birati Mahajati Nagar 3BHK House", "Independent double-storey home in quiet residential colony.", PropertyType.HOUSE, 7800000.00, 3, 2, 1600.0, "Mahajati Nagar, Birati 700051", 22.6610, 88.4350),
            ("Airport Enclave 2BHK Luxury Flat", "Furnished apartment ideal for airline crew and executives.", PropertyType.APARTMENT, 5200000.00, 2, 2, 960.0, "Jessore Road, Near Airport Gate 2 700081", 22.6510, 88.4425),
            ("Ganganagar IT Corridor 3BHK", "Fast-developing zone with quick access to New Town Expressway.", PropertyType.APARTMENT, 5100000.00, 3, 2, 1180.0, "Ganganagar More, Jessore Road 700132", 22.6810, 88.4560),

            # 32-35: New Barrackpore
            ("New Barrackpore Railview 2BHK", "Peaceful 2BHK flat 300 meters from New Barrackpore station.", PropertyType.APARTMENT, 3200000.00, 2, 1, 790.0, "Station Road, New Barrackpore 700131", 22.6860, 88.4470),
            ("Aparajita Residency 3BHK", "New construction project with lift, intercom, and water treatment.", PropertyType.APARTMENT, 4500000.00, 3, 2, 1110.0, "Bosepara, New Barrackpore 700131", 22.6895, 88.4520),
            ("New Barrackpore Independent Home", "Charming 3BHK single-owner house with small front lawn.", PropertyType.HOUSE, 6500000.00, 3, 2, 1480.0, "Ward 8, New Barrackpore 700131", 22.6840, 88.4500),
            ("Kalyani Expressway Link 2BHK Flat", "Strategic connectivity to IT hubs and industrial zones.", PropertyType.APARTMENT, 3400000.00, 2, 2, 830.0, "Kalyani Link Road, New Barrackpore 700131", 22.6920, 88.4430),

            # 36-42: Madhyamgram & Doltala
            ("Star Mall Adjacent 3BHK Luxury Flat", "Live right next to shopping, dining, and multiplex on Jessore Rd.", PropertyType.APARTMENT, 6100000.00, 3, 2, 1310.0, "Jessore Road, Madhyamgram 700129", 22.6955, 88.4715),
            ("Madhyamgram Chowmatha 2BHK", "Centrally located flat near auto stand, market, and schools.", PropertyType.APARTMENT, 3600000.00, 2, 1, 850.0, "Chowmatha, Madhyamgram 700129", 22.6990, 88.4650),
            ("Doltala Green Enclave 3BHK", "Lush green gated complex with indoor games room and gym.", PropertyType.APARTMENT, 5400000.00, 3, 2, 1220.0, "Doltala More, Madhyamgram 700132", 22.7040, 88.4680),
            ("Sodepur Road Madhyamgram 2BHK", "Direct connection between Sodepur BT Road and Madhyamgram station.", PropertyType.APARTMENT, 3300000.00, 2, 1, 810.0, "Sodepur Road, Madhyamgram 700129", 22.7010, 88.4590),
            ("Madhyamgram Badu Road 3BHK Villa", "Modern duplex villa with open sky private terrace.", PropertyType.VILLA, 8200000.00, 3, 3, 1850.0, "Badu Road, Madhyamgram 700128", 22.7080, 88.4780),
            ("East Kodalia 2BHK Family Home", "Calm and serene residential neighborhood with sweet water supply.", PropertyType.APARTMENT, 2950000.00, 2, 1, 760.0, "East Kodalia, Madhyamgram 700129", 22.7030, 88.4740),
            ("Madhyamgram Flyover View 3BHK", "Premium corner flat with cross-ventilation on Jessore Road.", PropertyType.APARTMENT, 5750000.00, 3, 2, 1240.0, "Near Flyover, Madhyamgram 700129", 22.6970, 88.4690),

            # 43-50: Hridaypur & Barasat (Champadali, Duckbungalow, Colony)
            ("Hridaypur Station Link 2BHK Flat", "Just 2 minutes walk from Hridaypur local railway station.", PropertyType.APARTMENT, 2800000.00, 2, 1, 780.0, "Hridaypur Station Road, Barasat 700127", 22.7120, 88.4770),
            ("Barasat Champadali Central 3BHK", "Heart of Barasat with immediate access to buses, hospital, and rail.", PropertyType.APARTMENT, 5200000.00, 3, 2, 1250.0, "Champadali More, Barasat 700124", 22.7180, 88.4860),
            ("Barasat Duckbungalow 3BHK Flat", "Executive address near government offices and district court.", PropertyType.APARTMENT, 5500000.00, 3, 2, 1300.0, "Duckbungalow, Barasat, Kolkata 700124", 22.7235, 88.4835),
            ("Nabapally Barasat 2BHK Sunlit Home", "Reputed residential hub flat close to top schools and healthcare.", PropertyType.APARTMENT, 3100000.00, 2, 1, 840.0, "Nabapally, Barasat, Kolkata 700126", 22.7150, 88.4720),
            ("Barasat Colony Independent 4BHK House", "Large family bungalow with 2-car porch and front garden.", PropertyType.HOUSE, 8900000.00, 4, 3, 2100.0, "Guptipara, Barasat 700124", 22.7270, 88.4890),
            ("Barasat Station Road Commercial Space", "High footfall retail commercial space on main station road.", PropertyType.COMMERCIAL, 6200000.00, 1, 1, 750.0, "Station Road, Barasat 700124", 22.7210, 88.4830),
            ("Barasat Kazipara 3BHK Gated Residency", "Modern gated society featuring badminton court and children's park.", PropertyType.APARTMENT, 4750000.00, 3, 2, 1160.0, "Kazipara, Barasat 700125", 22.7310, 88.4790),
            ("Barasat NH-12 Highway Greens 3BHK Villa", "Luxury lifestyle villa in green suburbs with easy airport expressway drive.", PropertyType.VILLA, 9500000.00, 3, 3, 2050.0, "NH-12 Bypass, Barasat 700125", 22.7350, 88.4980),
        ]

        properties_created = 0
        for title, desc, p_type, price, beds, baths, sqft, addr, lat, lng in properties_catalog:
            _, created = Property.objects.get_or_create(
                title=title,
                defaults={
                    "description": desc,
                    "property_type": p_type,
                    "status": PropertyStatus.ACTIVE,
                    "price": price,
                    "bedrooms": beds,
                    "bathrooms": baths,
                    "area_sqft": sqft,
                    "address": addr,
                    "agent": agent,
                    "location": Point(lng, lat, srid=4326),
                }
            )
            if created:
                properties_created += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully created {properties_created} properties in North Kolkata up to Barasat!"))
        self.stdout.write(self.style.SUCCESS(f"Total properties now in database: {Property.objects.count()}"))

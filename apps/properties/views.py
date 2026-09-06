from rest_framework import generics, status, permissions, parsers
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q
from django.contrib.gis.geos import Point, GEOSGeometry, Polygon
from django.contrib.gis.measure import D
from .models import Property, PropertyStatus, PropertyImage, PropertyInquiry, InquiryStatus
from .serializers import PropertySerializer, PropertyImageSerializer, PropertyInquirySerializer
from .permissions import IsAgentOrAdminOrReadOnly


class PropertyListCreateView(generics.ListCreateAPIView):
    serializer_class = PropertySerializer
    permission_classes = [IsAgentOrAdminOrReadOnly]

    def get_queryset(self):
        queryset = Property.objects.filter(status=PropertyStatus.ACTIVE).select_related('agent')
        
        # Filtering parameters
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        bedrooms = self.request.query_params.get('bedrooms')
        property_type = self.request.query_params.get('property_type')

        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        if bedrooms:
            queryset = queryset.filter(bedrooms__gte=bedrooms)
        if property_type:
            queryset = queryset.filter(property_type=property_type)

        return queryset


class PropertyDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Property.objects.all().select_related('agent').prefetch_related('images')
    serializer_class = PropertySerializer
    permission_classes = [IsAgentOrAdminOrReadOnly]


class PropertyRadiusSearchView(APIView):
    """
    Search properties within a specified radius (km) from a latitude/longitude point using PostGIS.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        try:
            lat = float(request.query_params.get('lat'))
            lng = float(request.query_params.get('lng'))
            radius_km = float(request.query_params.get('radius_km', 5.0))
        except (TypeError, ValueError):
            return Response(
                {"error": "lat, lng, and radius_km must be valid floating point numbers"},
                status=status.HTTP_400_BAD_REQUEST
            )

        center_point = Point(lng, lat, srid=4326)
        properties = Property.objects.filter(
            status=PropertyStatus.ACTIVE,
            location__distance_lte=(center_point, D(km=radius_km))
        ).select_related('agent')

        serializer = PropertySerializer(properties, many=True)
        return Response({
            "center": {"lat": lat, "lng": lng},
            "radius_km": radius_km,
            "count": len(properties),
            "results": serializer.data
        })


class PropertyPolygonSearchView(APIView):
    """
    Search properties contained within a GeoJSON Polygon using PostGIS location__within.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        geojson_data = request.data.get('geojson')
        if not geojson_data:
            return Response({"error": "geojson polygon is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            import json
            geometry = GEOSGeometry(json.dumps(geojson_data), srid=4326)
            if geometry.geom_type not in ['Polygon', 'MultiPolygon']:
                return Response({"error": "Geometry must be Polygon or MultiPolygon"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Invalid GeoJSON: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        properties = Property.objects.filter(
            status=PropertyStatus.ACTIVE,
            location__within=geometry
        ).select_related('agent')

        serializer = PropertySerializer(properties, many=True)
        return Response({
            "count": len(properties),
            "results": serializer.data
        })


class PropertyBoundingBoxSearchView(APIView):
    """
    Search properties contained within a bounding box (viewport).
    Expects bbox parameter in format: minLng,minLat,maxLng,maxLat
    """
    permission_classes = [permissions.AllowAny]
    def get(self, request):
        bbox_str = request.query_params.get('bbox')
        if not bbox_str:
            return Response({"error": "bbox parameter is required (minLng,minLat,maxLng,maxLat)"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            bbox_coords = [float(c) for c in bbox_str.split(',')]
            if len(bbox_coords) != 4:
                raise ValueError
            
            # min_lng, min_lat, max_lng, max_lat
            bbox_polygon = Polygon.from_bbox(bbox_coords)
            bbox_polygon.srid = 4326
        except ValueError:
            return Response(
                {"error": "bbox must contain 4 comma-separated numbers (minLng,minLat,maxLng,maxLat)"},
                status=status.HTTP_400_BAD_REQUEST
            )

        properties = Property.objects.filter(
            status=PropertyStatus.ACTIVE,
            location__contained=bbox_polygon
        ).select_related('agent')

        serializer = PropertySerializer(properties, many=True)
        return Response({
            "count": len(properties),
            "results": serializer.data
        })


class PropertyNearestAmenitiesView(APIView):
    """
    Returns the nearest amenity in each category (Metro, Hospital, School, Mall, Park)
    for a given property using PostGIS KNN and geodetic distance calculations.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        try:
            property_obj = Property.objects.get(pk=pk)
        except Property.DoesNotExist:
            return Response(
                {"error": f"Property with id {pk} not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        from apps.amenities.services import AmenitySpatialService
        data = AmenitySpatialService.get_nearest_amenities_for_property(property_obj)
        return Response(data)


class PropertyLocationScoreView(APIView):
    """
    Computes and returns the deterministic composite location score (0-100)
    for a given property across the 5 lifestyle pillars:
    - Transport (30%)
    - Healthcare (20%)
    - Education (20%)
    - Shopping (15%)
    - Recreation (15%)
    Supports custom runtime weight overrides via query parameters.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        try:
            property_obj = Property.objects.get(pk=pk)
        except Property.DoesNotExist:
            return Response(
                {"error": f"Property with id {pk} not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Parse optional custom weights from query params
        custom_weights = {}
        for param in ["transport", "healthcare", "education", "shopping", "recreation"]:
            val = request.query_params.get(param)
            if val is not None:
                try:
                    custom_weights[param.capitalize()] = float(val)
                except ValueError:
                    pass

        from apps.amenities.services import AmenitySpatialService
        data = AmenitySpatialService.calculate_location_score_for_property(
            property_obj,
            custom_weights=custom_weights if custom_weights else None
        )
        return Response(data)


class AgentInventoryAPIView(APIView):
    """
    High-density asset inventory management API for licensed agents and platform administrators.
    - Agents only access listings they represent.
    - Admins access platform-wide inventory.
    - Supports search (title, address), status filtering, bedrooms, property_type, and ordering.
    - Returns aggregated status metrics across portfolio (total, active, under_offer, sold, rented, inactive).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if not (user.is_agent or user.is_platform_admin):
            return Response(
                {"error": "Only licensed agents and platform administrators may access inventory management."},
                status=status.HTTP_403_FORBIDDEN
            )

        if user.is_platform_admin:
            base_qs = Property.objects.all().select_related('agent')
        else:
            base_qs = Property.objects.filter(agent=user).select_related('agent')

        status_counts = {
            "total": base_qs.count(),
            "active": base_qs.filter(status=PropertyStatus.ACTIVE).count(),
            "under_offer": base_qs.filter(status=PropertyStatus.UNDER_OFFER).count(),
            "sold": base_qs.filter(status=PropertyStatus.SOLD).count(),
            "rented": base_qs.filter(status=PropertyStatus.RENTED).count(),
            "inactive": base_qs.filter(status=PropertyStatus.INACTIVE).count(),
        }

        qs = base_qs

        search_query = request.query_params.get('search', '').strip()
        if search_query:
            qs = qs.filter(
                Q(title__icontains=search_query) |
                Q(address__icontains=search_query)
            )

        status_filter = request.query_params.get('status', '').strip().upper()
        if status_filter and status_filter != 'ALL':
            qs = qs.filter(status=status_filter)

        bedrooms = request.query_params.get('bedrooms')
        if bedrooms:
            try:
                bhk_val = int(bedrooms)
                if bhk_val >= 4:
                    qs = qs.filter(bedrooms__gte=4)
                else:
                    qs = qs.filter(bedrooms=bhk_val)
            except ValueError:
                pass

        prop_type = request.query_params.get('property_type', '').strip().upper()
        if prop_type and prop_type != 'ALL':
            qs = qs.filter(property_type=prop_type)

        ordering = request.query_params.get('ordering', '-created_at')
        allowed_orderings = {
            '-created_at', 'created_at',
            'price', '-price',
            'area_sqft', '-area_sqft',
            'bedrooms', '-bedrooms',
            'title', '-title'
        }
        if ordering in allowed_orderings:
            qs = qs.order_by(ordering)
        else:
            qs = qs.order_by('-created_at')

        serializer = PropertySerializer(qs, many=True)
        return Response({
            "status_counts": status_counts,
            "count": len(qs),
            "results": serializer.data
        })


class PropertyImageUploadView(APIView):
    """
    Upload one or multiple gallery images for a property.
    Restricted to the listing's agent or platform administrators.
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def post(self, request, pk):
        try:
            property_obj = Property.objects.get(pk=pk)
        except Property.DoesNotExist:
            return Response({"error": "Property not found"}, status=status.HTTP_404_NOT_FOUND)

        if not (request.user.is_platform_admin or property_obj.agent == request.user):
            return Response(
                {"error": "You do not have permission to upload images for this listing."},
                status=status.HTTP_403_FORBIDDEN
            )

        files = request.FILES.getlist('images')
        if not files and 'image' in request.FILES:
            files = [request.FILES['image']]

        if not files:
            return Response({"error": "No image files provided."}, status=status.HTTP_400_BAD_REQUEST)

        caption = request.data.get('caption', '')
        is_primary = str(request.data.get('is_primary', 'false')).lower() in ['true', '1']

        has_existing_images = property_obj.images.exists()
        if not has_existing_images:
            is_primary = True

        created_images = []
        for idx, file_obj in enumerate(files):
            set_as_primary = is_primary if idx == 0 else False
            if set_as_primary:
                property_obj.images.filter(is_primary=True).update(is_primary=False)

            img = PropertyImage.objects.create(
                property=property_obj,
                image=file_obj,
                caption=caption,
                is_primary=set_as_primary
            )
            created_images.append(img)

        serializer = PropertyImageSerializer(created_images, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PropertyImageDetailView(APIView):
    """
    Manage an individual property gallery image (delete or toggle primary badge).
    Restricted to the listing's agent or platform administrators.
    """
    permission_classes = [permissions.IsAuthenticated]

    def _get_property_and_image(self, request, pk, image_id):
        try:
            property_obj = Property.objects.get(pk=pk)
        except Property.DoesNotExist:
            return None, None, Response({"error": "Property not found"}, status=status.HTTP_404_NOT_FOUND)

        if not (request.user.is_platform_admin or property_obj.agent == request.user):
            return None, None, Response(
                {"error": "You do not have permission to modify images for this listing."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            image_obj = property_obj.images.get(pk=image_id)
        except PropertyImage.DoesNotExist:
            return None, None, Response({"error": "Image not found"}, status=status.HTTP_404_NOT_FOUND)

        return property_obj, image_obj, None

    def delete(self, request, pk, image_id):
        prop, image_obj, error_resp = self._get_property_and_image(request, pk, image_id)
        if error_resp:
            return error_resp

        was_primary = image_obj.is_primary
        if image_obj.image:
            image_obj.image.delete(save=False)
        image_obj.delete()

        if was_primary:
            remaining = prop.images.first()
            if remaining:
                remaining.is_primary = True
                remaining.save(update_fields=['is_primary'])

        return Response({"message": "Image deleted successfully"}, status=status.HTTP_200_OK)

    def patch(self, request, pk, image_id):
        prop, image_obj, error_resp = self._get_property_and_image(request, pk, image_id)
        if error_resp:
            return error_resp

        if 'is_primary' in request.data:
            is_primary = str(request.data['is_primary']).lower() in ['true', '1']
            if is_primary:
                prop.images.filter(is_primary=True).update(is_primary=False)
                image_obj.is_primary = True
            else:
                image_obj.is_primary = False

        if 'caption' in request.data:
            image_obj.caption = str(request.data['caption'])

        image_obj.save()
        serializer = PropertyImageSerializer(image_obj)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PropertyInquiryCreateView(APIView):
    """
    Public or authenticated buyer inquiry submission for an active property.
    Supports scheduling a preferred site visit date.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, pk):
        try:
            property_obj = Property.objects.select_related('agent').get(pk=pk)
        except Property.DoesNotExist:
            return Response({"error": "Property not found"}, status=status.HTTP_404_NOT_FOUND)

        buyer_user = request.user if request.user.is_authenticated else None

        name = request.data.get('name', '').strip()
        email = request.data.get('email', '').strip()
        phone = request.data.get('phone', '').strip()
        message = request.data.get('message', '').strip()
        preferred_visit_date = request.data.get('preferred_visit_date', None)

        if buyer_user:
            if not name:
                name = buyer_user.get_full_name() or buyer_user.username
            if not email:
                email = buyer_user.email

        if not name:
            return Response({"error": "Name is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not email:
            return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Parse preferred_visit_date if provided
        if preferred_visit_date == '':
            preferred_visit_date = None

        inquiry = PropertyInquiry.objects.create(
            property=property_obj,
            buyer=buyer_user,
            name=name,
            email=email,
            phone=phone,
            message=message,
            preferred_visit_date=preferred_visit_date,
            status=InquiryStatus.NEW
        )

        serializer = PropertyInquirySerializer(inquiry)
        return Response({
            "message": "Your inquiry and site visit request have been registered with the listing agent.",
            "inquiry": serializer.data
        }, status=status.HTTP_201_CREATED)


class AgentLeadsAPIView(APIView):
    """
    Lead CRM pipeline management API for licensed agents and platform administrators.
    - Agents access inquiries for their represented properties.
    - Admins access platform-wide leads.
    - Supports search, status filtering, and property filtering.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if not (user.is_agent or user.is_platform_admin):
            return Response(
                {"error": "Only licensed agents and platform administrators may access leads management."},
                status=status.HTTP_403_FORBIDDEN
            )

        if user.is_platform_admin:
            base_qs = PropertyInquiry.objects.all().select_related('property', 'buyer', 'property__agent')
        else:
            base_qs = PropertyInquiry.objects.filter(property__agent=user).select_related('property', 'buyer', 'property__agent')

        status_counts = {
            "total": base_qs.count(),
            "new": base_qs.filter(status=InquiryStatus.NEW).count(),
            "contacted": base_qs.filter(status=InquiryStatus.CONTACTED).count(),
            "site_visit": base_qs.filter(status=InquiryStatus.SITE_VISIT).count(),
            "negotiation": base_qs.filter(status=InquiryStatus.NEGOTIATION).count(),
            "closed": base_qs.filter(status=InquiryStatus.CLOSED).count(),
            "lost": base_qs.filter(status=InquiryStatus.LOST).count(),
        }

        qs = base_qs

        # Search parameter
        search_query = request.query_params.get('search', '').strip()
        if search_query:
            qs = qs.filter(
                Q(name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(phone__icontains=search_query) |
                Q(property__title__icontains=search_query)
            )

        # Status filter
        status_filter = request.query_params.get('status', '').strip().upper()
        if status_filter and status_filter != 'ALL':
            qs = qs.filter(status=status_filter)

        # Property ID filter
        property_id = request.query_params.get('property_id')
        if property_id:
            qs = qs.filter(property_id=property_id)

        # Ordering
        ordering = request.query_params.get('ordering', '-created_at')
        allowed_orderings = {'-created_at', 'created_at', 'preferred_visit_date', '-preferred_visit_date', 'name', '-name'}
        if ordering in allowed_orderings:
            qs = qs.order_by(ordering)
        else:
            qs = qs.order_by('-created_at')

        serializer = PropertyInquirySerializer(qs, many=True)
        return Response({
            "status_counts": status_counts,
            "count": len(qs),
            "results": serializer.data
        })


class AgentLeadDetailView(APIView):
    """
    Update inquiry status or append internal agent notes.
    Delete inquiry.
    """
    permission_classes = [permissions.IsAuthenticated]

    def _get_inquiry(self, request, pk):
        try:
            inquiry = PropertyInquiry.objects.select_related('property', 'property__agent').get(pk=pk)
        except PropertyInquiry.DoesNotExist:
            return None, Response({"error": "Inquiry not found"}, status=status.HTTP_404_NOT_FOUND)

        if not (request.user.is_platform_admin or inquiry.property.agent == request.user):
            return None, Response(
                {"error": "You do not have permission to manage this buyer lead."},
                status=status.HTTP_403_FORBIDDEN
            )

        return inquiry, None

    def patch(self, request, pk):
        inquiry, error_resp = self._get_inquiry(request, pk)
        if error_resp:
            return error_resp

        if 'status' in request.data:
            new_status = request.data['status'].strip().upper()
            if new_status in InquiryStatus.values:
                inquiry.status = new_status
            else:
                return Response({"error": f"Invalid status '{new_status}'."}, status=status.HTTP_400_BAD_REQUEST)

        if 'agent_notes' in request.data:
            inquiry.agent_notes = str(request.data['agent_notes'])

        inquiry.save()
        serializer = PropertyInquirySerializer(inquiry)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        inquiry, error_resp = self._get_inquiry(request, pk)
        if error_resp:
            return error_resp

        inquiry.delete()
        return Response({"message": "Buyer lead deleted successfully."}, status=status.HTTP_200_OK)



class PropertyCompareAPIView(APIView):
    """
    Compares 2 to 4 properties side-by-side.
    Returns serialized properties enriched with their Location Scores.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        property_ids = request.data.get('property_ids', [])
        
        if not isinstance(property_ids, list):
            return Response({"error": "property_ids must be a list"}, status=status.HTTP_400_BAD_REQUEST)
            
        # We allow exactly 2 to 4 properties for a side-by-side comparison matrix
        if not (2 <= len(property_ids) <= 4):
            return Response({"error": "Please select between 2 and 4 properties to compare."}, status=status.HTTP_400_BAD_REQUEST)
            
        # Fetch properties ensuring they are ACTIVE
        properties = Property.objects.filter(id__in=property_ids, status=PropertyStatus.ACTIVE).select_related('agent').prefetch_related('images')
        
        if len(properties) != len(property_ids):
            return Response({"error": "One or more properties could not be found or are inactive."}, status=status.HTTP_404_NOT_FOUND)
            
        # Maintain the requested order
        prop_dict = {p.id: p for p in properties}
        ordered_properties = [prop_dict[pid] for pid in property_ids if pid in prop_dict]
            
        serializer = PropertySerializer(ordered_properties, many=True)
        results = serializer.data
        
        # Enrich with Location Scores and Amenity Proximity
        from apps.amenities.services import AmenitySpatialService
        for item, prop_obj in zip(results, ordered_properties):
            score_data = AmenitySpatialService.calculate_location_score_for_property(prop_obj)
            item['location_score'] = score_data
            
        return Response({
            "count": len(results),
            "results": results
        })

class AreaAnalyticsAPIView(APIView):
    """
    Returns aggregated spatial market analytics for properties within a bounding box.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        bbox_str = request.query_params.get('bbox')
        if not bbox_str:
            return Response({"error": "bbox parameter is required (minLng,minLat,maxLng,maxLat)"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            bbox_coords = [float(c) for c in bbox_str.split(',')]
            if len(bbox_coords) != 4:
                raise ValueError
            bbox_polygon = Polygon.from_bbox(bbox_coords)
            bbox_polygon.srid = 4326
        except ValueError:
            return Response(
                {"error": "bbox must contain 4 comma-separated numbers (minLng,minLat,maxLng,maxLat)"},
                status=status.HTTP_400_BAD_REQUEST
            )

        properties = Property.objects.filter(
            status=PropertyStatus.ACTIVE,
            location__contained=bbox_polygon
        )
        
        from django.db.models import Avg, Count, Max, Min, F, FloatField, ExpressionWrapper
        
        properties_annotated = properties.annotate(
            price_sqft=ExpressionWrapper(F('price') / F('area_sqft'), output_field=FloatField())
        )

        stats = properties_annotated.aggregate(
            total_properties=Count('id'),
            avg_price=Avg('price'),
            min_price=Min('price'),
            max_price=Max('price'),
            avg_price_sqft=Avg('price_sqft'),
            avg_area_sqft=Avg('area_sqft')
        )
        
        # Breakdown by property type
        type_breakdown = list(properties.values('property_type').annotate(count=Count('id')).order_by('-count'))
        
        # Approximate Median Price in Python
        prices = list(properties.values_list('price', flat=True))
        median_price = None
        if prices:
            prices.sort()
            n = len(prices)
            if n % 2 == 0:
                median_price = (float(prices[n//2 - 1]) + float(prices[n//2])) / 2.0
            else:
                median_price = float(prices[n//2])

        return Response({
            "bbox": bbox_coords,
            "stats": {
                "total_properties": stats['total_properties'] or 0,
                "avg_price": float(stats['avg_price']) if stats['avg_price'] else None,
                "median_price": median_price,
                "min_price": float(stats['min_price']) if stats['min_price'] else None,
                "max_price": float(stats['max_price']) if stats['max_price'] else None,
                "avg_price_sqft": float(stats['avg_price_sqft']) if stats['avg_price_sqft'] else None,
                "avg_area_sqft": float(stats['avg_area_sqft']) if stats['avg_area_sqft'] else None,
            },
            "type_breakdown": type_breakdown
        })

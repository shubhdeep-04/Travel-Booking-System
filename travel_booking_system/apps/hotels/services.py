"""
Business logic and services for Hotel operations.
"""

from django.db import transaction
from django.db.models import Q, F, Sum, Count, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple, Dict
import logging

logger = logging.getLogger(__name__)


class HotelSearchService:
    """Service for searching and filtering hotels."""
    
    @staticmethod
    def search_hotels(
        city: str = None,
        check_in: datetime = None,
        check_out: datetime = None,
        guests: int = 1,
        rooms: int = 1,
        min_price: Decimal = None,
        max_price: Decimal = None,
        star_rating: int = None,
        amenities: List[str] = None,
        sort_by: str = 'rating',
        page: int = 1,
        page_size: int = 10
    ) -> Dict:
        """
        Search hotels with filters.
        In production, this would integrate with a search engine like Elasticsearch.
        """
        from .models import Hotel, HotelRoom
        
        filters = Q(is_active=True)
        
        # City filter
        if city:
            filters &= Q(city__icontains=city) | Q(state__icontains=city)
        
        # Star rating filter
        if star_rating:
            filters &= Q(star_rating__gte=star_rating)
        
        # Amenities filter
        if amenities:
            for amenity in amenities:
                # Map amenity string to model field
                amenity_map = {
                    'wifi': 'has_wifi',
                    'pool': 'has_pool',
                    'gym': 'has_gym',
                    'spa': 'has_spa',
                    'restaurant': 'has_restaurant',
                    'parking': 'has_parking',
                    'shuttle': 'has_airport_shuttle',
                    'pet_friendly': 'is_pet_friendly',
                }
                if amenity in amenity_map:
                    filters &= Q(**{amenity_map[amenity]: True})
        
        # Get hotels
        hotels = Hotel.objects.filter(filters)
        
        # Price filter (requires room availability check)
        if min_price is not None or max_price is not None:
            hotel_ids = HotelRoom.objects.filter(
                is_available=True,
                available_rooms__gte=rooms
            )
            
            if min_price is not None:
                hotel_ids = hotel_ids.filter(base_price__gte=min_price)
            if max_price is not None:
                hotel_ids = hotel_ids.filter(base_price__lte=max_price)
            
            hotel_ids = hotel_ids.values_list('hotel_id', flat=True).distinct()
            hotels = hotels.filter(id__in=hotel_ids)
        
        # Sort results
        sort_map = {
            'price_low': 'rooms__base_price',
            'price_high': '-rooms__base_price',
            'rating': '-avg_rating',
            'star': '-star_rating',
            'name': 'name',
        }
        sort_field = sort_map.get(sort_by, '-avg_rating')
        
        hotels = hotels.order_by(sort_field).distinct()
        
        # Pagination
        total = hotels.count()
        start = (page - 1) * page_size
        end = start + page_size
        hotels_page = hotels[start:end]
        
        return {
            'hotels': hotels_page,
            'total': total,
            'page': page,
            'page_size': page_size,
            'pages': (total + page_size - 1) // page_size
        }
    
    @staticmethod
    def get_available_rooms(
        hotel_id: str,
        check_in: datetime,
        check_out: datetime,
        guests: int = 1,
        rooms: int = 1
    ) -> List:
        """Get available rooms for specific dates."""
        from .models import HotelRoom
        
        # In production, this would check against existing bookings
        # For now, we'll just check room availability
        
        rooms = HotelRoom.objects.filter(
            hotel_id=hotel_id,
            is_available=True,
            available_rooms__gte=rooms,
            max_guests__gte=guests
        ).select_related('room_type', 'hotel')
        
        return rooms
    
    @staticmethod
    def get_hotel_recommendations(user_id: str = None, limit: int = 10) -> List:
        """Get hotel recommendations based on user preferences or popular hotels."""
        from .models import Hotel
        
        if user_id:
            # In production: Implement collaborative filtering
            # For now, return featured hotels
            return Hotel.objects.filter(
                is_active=True,
                featured=True
            ).order_by('-avg_rating')[:limit]
        
        # Return popular hotels (based on review count)
        return Hotel.objects.filter(
            is_active=True
        ).order_by('-review_count', '-avg_rating')[:limit]


class HotelBookingService:
    """Service for handling hotel bookings."""
    
    @staticmethod
    @transaction.atomic
    def create_booking(
        user,
        hotel_id: str,
        room_type_id: str,
        check_in: datetime,
        check_out: datetime,
        rooms: int = 1,
        guests: int = 1,
        special_requests: str = ''
    ) -> Tuple[bool, dict, str]:
        """
        Create a hotel booking with transaction safety.
        Returns: (success, booking_data, error_message)
        """
        from .models import Hotel, HotelRoom
        from apps.bookings.models import Booking
        
        try:
            # Get hotel and room
            hotel = Hotel.objects.get(id=hotel_id, is_active=True)
            room_type = HotelRoom.objects.select_for_update().get(
                hotel=hotel,
                id=room_type_id,
                is_available=True,
                available_rooms__gte=rooms,
                max_guests__gte=guests
            )
            
            # Calculate stay duration
            nights = (check_out - check_in).days
            if nights <= 0:
                return False, None, "Check-out date must be after check-in date"
            
            # Calculate price
            room_price = room_type.final_price
            total_price = room_price * rooms * nights
            
            # Create booking
            booking = Booking.objects.create(
                user=user,
                service_type=Booking.ServiceType.HOTEL,
                service_id=hotel_id,
                check_in_date=check_in,
                check_out_date=check_out,
                total_amount=total_price,
                status=Booking.Status.PENDING,
                metadata={
                    'hotel_name': hotel.name,
                    'room_type': room_type.name,
                    'room_type_id': str(room_type.id),
                    'rooms': rooms,
                    'guests': guests,
                    'nights': nights,
                    'room_price': str(room_price),
                    'special_requests': special_requests,
                }
            )
            
            # Reserve rooms
            room_type.reserve_rooms(rooms)
            
            # Prepare booking data
            booking_data = {
                'booking_id': str(booking.id),
                'hotel_name': hotel.name,
                'room_type': room_type.name,
                'check_in': check_in,
                'check_out': check_out,
                'nights': nights,
                'rooms': rooms,
                'guests': guests,
                'total_amount': total_price,
                'booking_date': booking.created_at,
            }
            
            logger.info(f"Hotel booking created: {booking.id} for user {user.id}")
            return True, booking_data, None
            
        except Hotel.DoesNotExist:
            return False, None, "Hotel not found or not active"
        except HotelRoom.DoesNotExist:
            return False, None, "Room not available or insufficient capacity"
        except Exception as e:
            logger.error(f"Error creating hotel booking: {str(e)}")
            return False, None, f"Booking failed: {str(e)}"
    
    @staticmethod
    @transaction.atomic
    def cancel_booking(booking_id: str, user) -> Tuple[bool, str]:
        """Cancel a hotel booking and release rooms."""
        from apps.bookings.models import Booking
        
        try:
            booking = Booking.objects.select_for_update().get(
                id=booking_id,
                user=user,
                service_type=Booking.ServiceType.HOTEL
            )
            
            # Check cancellation policy
            from .models import HotelRoom
            try:
                room_type = HotelRoom.objects.get(id=booking.metadata.get('room_type_id'))
                
                # Calculate cancellation fee based on policy
                days_before_checkin = (booking.check_in_date - timezone.now()).days
                cancellation_fee = Decimal('0.00')
                
                if days_before_checkin < room_type.cancellation_days:
                    cancellation_fee = room_type.get_cancellation_fee(booking.total_amount)
                
                # Update booking status
                booking.status = Booking.Status.CANCELLED
                booking.cancellation_fee = cancellation_fee
                booking.cancelled_at = timezone.now()
                booking.save()
                
                # Release rooms
                rooms_to_release = booking.metadata.get('rooms', 1)
                room_type.release_rooms(rooms_to_release)
                
                logger.info(f"Hotel booking cancelled: {booking_id}")
                return True, f"Cancelled successfully. Cancellation fee: ${cancellation_fee}"
                
            except HotelRoom.DoesNotExist:
                return False, "Room type not found"
                
        except Booking.DoesNotExist:
            return False, "Booking not found"
        except Exception as e:
            logger.error(f"Error cancelling hotel booking: {str(e)}")
            return False, f"Cancellation failed: {str(e)}"


class HotelAnalyticsService:
    """Service for hotel analytics and reporting."""
    
    @staticmethod
    def get_hotel_analytics(hotel_id: str, start_date: datetime, end_date: datetime) -> Dict:
        """Get analytics for a specific hotel."""
        from .models import Hotel
        from apps.bookings.models import Booking
        
        try:
            hotel = Hotel.objects.get(id=hotel_id)
            
            # Get bookings for the period
            bookings = Booking.objects.filter(
                service_type=Booking.ServiceType.HOTEL,
                service_id=hotel_id,
                created_at__range=[start_date, end_date]
            )
            
            # Calculate metrics
            total_bookings = bookings.count()
            confirmed_bookings = bookings.filter(status=Booking.Status.CONFIRMED).count()
            cancelled_bookings = bookings.filter(status=Booking.Status.CANCELLED).count()
            
            revenue = bookings.filter(
                status=Booking.Status.CONFIRMED
            ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
            
            cancellation_rate = (cancelled_bookings / total_bookings * 100) if total_bookings > 0 else 0
            
            # Get occupancy rate (simplified)
            # In production, calculate based on room nights
            occupancy_rate = min((confirmed_bookings * 100) / hotel.available_rooms, 100) if hotel.available_rooms > 0 else 0
            
            return {
                'hotel': hotel.name,
                'period': {
                    'start': start_date,
                    'end': end_date
                },
                'metrics': {
                    'total_bookings': total_bookings,
                    'confirmed_bookings': confirmed_bookings,
                    'cancelled_bookings': cancelled_bookings,
                    'revenue': revenue,
                    'cancellation_rate': round(cancellation_rate, 2),
                    'occupancy_rate': round(occupancy_rate, 2),
                }
            }
            
        except Hotel.DoesNotExist:
            return None
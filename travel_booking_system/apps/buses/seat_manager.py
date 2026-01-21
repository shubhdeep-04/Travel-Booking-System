"""
Seat management for bus bookings with transaction safety.
"""

from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import logging
from typing import List, Tuple, Optional, Dict

logger = logging.getLogger(__name__)


class SeatManager:
    """Manage bus seat booking and availability."""
    
    @staticmethod
    @transaction.atomic
    def book_seats(
        bus_id: str,
        seat_numbers: List[str],
        travel_date: datetime.date,
        user_id: str
    ) -> Tuple[bool, List[str], Decimal, str]:
        """
        Book multiple seats for a bus journey.
        Returns: (success, booked_seats, total_amount, error_message)
        """
        from .models import Bus, BusSeat
        
        try:
            bus = Bus.objects.select_for_update().get(id=bus_id)
            
            # Check if travel date is valid
            if travel_date < timezone.now().date():
                return False, [], Decimal('0.00'), "Travel date cannot be in the past"
            
            # Get seats to book
            seats = BusSeat.objects.select_for_update().filter(
                bus=bus,
                seat_number__in=seat_numbers,
                is_booked=False,
                is_blocked=False
            )
            
            # Check if all requested seats are available
            available_seat_numbers = [seat.seat_number for seat in seats]
            unavailable_seats = set(seat_numbers) - set(available_seat_numbers)
            
            if unavailable_seats:
                return False, [], Decimal('0.00'), f"Seats {unavailable_seats} are not available"
            
            # Calculate total amount
            total_amount = Decimal('0.00')
            for seat in seats:
                total_amount += seat.final_fare
            
            # Mark seats as booked
            seats.update(is_booked=True)
            
            logger.info(f"Booked seats {seat_numbers} on bus {bus.bus_number} for {travel_date}")
            return True, seat_numbers, total_amount, ""
            
        except Bus.DoesNotExist:
            return False, [], Decimal('0.00'), "Bus not found"
        except Exception as e:
            logger.error(f"Error booking seats: {str(e)}")
            return False, [], Decimal('0.00'), f"Booking failed: {str(e)}"
    
    @staticmethod
    @transaction.atomic
    def release_seats(bus_id: str, seat_numbers: List[str]) -> Tuple[bool, str]:
        """Release booked seats."""
        from .models import BusSeat
        
        try:
            seats = BusSeat.objects.select_for_update().filter(
                bus_id=bus_id,
                seat_number__in=seat_numbers,
                is_booked=True
            )
            
            seats.update(is_booked=False)
            logger.info(f"Released seats {seat_numbers} on bus {bus_id}")
            return True, ""
            
        except Exception as e:
            logger.error(f"Error releasing seats: {str(e)}")
            return False, f"Failed to release seats: {str(e)}"
    
    @staticmethod
    @transaction.atomic
    def block_seats(
        bus_id: str,
        seat_numbers: List[str],
        reason: str = "",
        block_duration_minutes: int = 15
    ) -> Tuple[bool, str]:
        """Temporarily block seats (for payment processing)."""
        from .models import BusSeat
        
        try:
            seats = BusSeat.objects.select_for_update().filter(
                bus_id=bus_id,
                seat_number__in=seat_numbers,
                is_booked=False,
                is_blocked=False
            )
            
            # Create a temporary block
            # In production, you'd have a SeatBlock model with expiration
            seats.update(
                is_blocked=True,
                block_reason=reason
            )
            
            logger.info(f"Blocked seats {seat_numbers} on bus {bus_id} for {block_duration_minutes} minutes")
            return True, ""
            
        except Exception as e:
            logger.error(f"Error blocking seats: {str(e)}")
            return False, f"Failed to block seats: {str(e)}"
    
    @staticmethod
    def get_seat_layout(bus_id: str) -> Dict:
        """Get bus seat layout with availability status."""
        from .models import Bus, BusSeat
        
        try:
            bus = Bus.objects.get(id=bus_id)
            seats = BusSeat.objects.filter(bus=bus).order_by('row_number', 'column_number')
            
            # Group seats by row
            layout = {}
            for seat in seats:
                if seat.row_number not in layout:
                    layout[seat.row_number] = []
                
                layout[seat.row_number].append({
                    'seat_number': seat.seat_number,
                    'seat_type': seat.seat_type,
                    'seat_gender': seat.seat_gender,
                    'is_available': seat.is_available,
                    'is_booked': seat.is_booked,
                    'is_blocked': seat.is_blocked,
                    'fare_adjustment': float(seat.fare_adjustment),
                    'final_fare': float(seat.final_fare),
                    'is_emergency_exit': seat.is_emergency_exit,
                    'is_near_toilet': seat.is_near_toilet,
                })
            
            return {
                'bus_id': str(bus.id),
                'bus_number': bus.bus_number,
                'total_seats': bus.total_seats,
                'seats_per_row': bus.seats_per_row,
                'seat_layout': bus.seat_layout,
                'rows': layout,
                'available_seats': bus.available_seats,
                'is_full': bus.is_full,
            }
            
        except Bus.DoesNotExist:
            return {}
    
    @staticmethod
    def get_available_seats_for_date(bus_id: str, travel_date: datetime.date) -> List[str]:
        """Get available seats for specific travel date."""
        from .models import Bus, BusBooking, BusSeat
        
        try:
            bus = Bus.objects.get(id=bus_id)
            
            # Get booked seats for this date
            booked_bookings = BusBooking.objects.filter(
                bus=bus,
                travel_date=travel_date,
                status__in=['CONFIRMED', 'PENDING']
            )
            
            booked_seats = []
            for booking in booked_bookings:
                booked_seats.extend(booking.seats_booked)
            
            # Get all seats excluding booked ones
            available_seats = BusSeat.objects.filter(
                bus=bus,
                is_booked=False,
                is_blocked=False
            ).exclude(seat_number__in=booked_seats)
            
            return [seat.seat_number for seat in available_seats]
            
        except Bus.DoesNotExist:
            return []
    
    @staticmethod
    def validate_seat_selection(
        bus_id: str,
        seat_numbers: List[str],
        passenger_gender: str = None
    ) -> Tuple[bool, str]:
        """Validate seat selection rules."""
        from .models import BusSeat
        
        try:
            seats = BusSeat.objects.filter(
                bus_id=bus_id,
                seat_number__in=seat_numbers
            )
            
            # Check gender restrictions
            if passenger_gender:
                for seat in seats:
                    if seat.seat_gender != 'ANY' and seat.seat_gender != passenger_gender:
                        return False, f"Seat {seat.seat_number} is restricted to {seat.seat_gender} passengers"
            
            # Check if all seats are in same row (for group booking)
            rows = set(seat.row_number for seat in seats)
            if len(rows) > 1 and len(seat_numbers) > 1:
                # Allow multiple rows but warn
                pass
            
            # Check emergency exit seats (might have restrictions)
            emergency_exit_seats = [seat for seat in seats if seat.is_emergency_exit]
            if emergency_exit_seats:
                # In production, you might have age restrictions for emergency exit seats
                pass
            
            return True, ""
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"


class SeatPricingManager:
    """Manage dynamic seat pricing."""
    
    @staticmethod
    def calculate_dynamic_fare(
        bus_id: str,
        seat_numbers: List[str],
        travel_date: datetime.date,
        booking_date: datetime.date = None
    ) -> Dict[str, Decimal]:
        """Calculate dynamic fares based on various factors."""
        from .models import Bus, BusSeat
        
        if booking_date is None:
            booking_date = timezone.now().date()
        
        try:
            bus = Bus.objects.get(id=bus_id)
            seats = BusSeat.objects.filter(bus=bus, seat_number__in=seat_numbers)
            
            # Base calculation
            seat_fares = {}
            for seat in seats:
                base_fare = seat.final_fare
                
                # Apply dynamic pricing factors
                dynamic_fare = base_fare
                
                # 1. Days before travel (last-minute booking premium)
                days_before = (travel_date - booking_date).days
                if days_before <= 1:
                    # Last minute: +20%
                    dynamic_fare *= Decimal('1.20')
                elif days_before <= 3:
                    # 1-3 days: +10%
                    dynamic_fare *= Decimal('1.10')
                elif days_before >= 30:
                    # Early bird: -10%
                    dynamic_fare *= Decimal('0.90')
                
                # 2. Seat type premium
                if seat.seat_type == 'WINDOW':
                    dynamic_fare *= Decimal('1.05')  # 5% premium
                elif seat.seat_type == 'SLEEPER':
                    dynamic_fare *= Decimal('1.15')  # 15% premium
                
                # 3. Seat position premium (emergency exit might be cheaper)
                if seat.is_emergency_exit:
                    dynamic_fare *= Decimal('0.95')  # 5% discount
                if seat.is_near_toilet:
                    dynamic_fare *= Decimal('0.90')  # 10% discount
                
                # 4. Bus occupancy (if high occupancy, increase price)
                occupancy_rate = (bus.total_seats - bus.available_seats) / bus.total_seats
                if occupancy_rate > 0.8:  # 80% occupied
                    dynamic_fare *= Decimal('1.10')  # 10% premium
                elif occupancy_rate < 0.3:  # Less than 30% occupied
                    dynamic_fare *= Decimal('0.95')  # 5% discount
                
                seat_fares[seat.seat_number] = dynamic_fare
            
            return seat_fares
            
        except Exception as e:
            logger.error(f"Error calculating dynamic fare: {str(e)}")
            return {}


class SeatAutoAllocator:
    """Automatically allocate seats based on preferences."""
    
    @staticmethod
    def allocate_seats(
        bus_id: str,
        num_seats: int,
        preferences: Dict = None
    ) -> List[str]:
        """
        Automatically allocate seats based on preferences.
        Preferences can include:
        - seat_type: 'WINDOW', 'AISLE', 'SLEEPER'
        - seat_gender: 'MALE', 'FEMALE', 'ANY'
        - avoid_near_toilet: True/False
        - avoid_emergency_exit: True/False
        - prefer_together: True/False (for group)
        """
        from .models import BusSeat
        
        if preferences is None:
            preferences = {}
        
        try:
            # Build query filters
            filters = {
                'bus_id': bus_id,
                'is_booked': False,
                'is_blocked': False,
            }
            
            if preferences.get('seat_type'):
                filters['seat_type'] = preferences['seat_type']
            
            if preferences.get('seat_gender'):
                filters['seat_gender'] = preferences['seat_gender']
            
            if preferences.get('avoid_near_toilet'):
                filters['is_near_toilet'] = False
            
            if preferences.get('avoid_emergency_exit'):
                filters['is_emergency_exit'] = False
            
            # Get available seats
            available_seats = BusSeat.objects.filter(**filters).order_by(
                'row_number', 'column_number'
            )
            
            if num_seats == 1:
                # Single seat allocation
                if available_seats.exists():
                    return [available_seats.first().seat_number]
            
            elif num_seats > 1 and preferences.get('prefer_together'):
                # Group allocation - try to find seats together
                seats_by_row = {}
                for seat in available_seats:
                    if seat.row_number not in seats_by_row:
                        seats_by_row[seat.row_number] = []
                    seats_by_row[seat.row_number].append(seat)
                
                # Find row with enough consecutive seats
                for row_num, seats in seats_by_row.items():
                    if len(seats) >= num_seats:
                        # Return first N seats in this row
                        return [seat.seat_number for seat in seats[:num_seats]]
                
                # If no row has enough seats, return any available seats
                return [seat.seat_number for seat in available_seats[:num_seats]]
            
            else:
                # Multiple seats, no preference for together
                return [seat.seat_number for seat in available_seats[:num_seats]]
            
            return []
            
        except Exception as e:
            logger.error(f"Error allocating seats: {str(e)}")
            return []
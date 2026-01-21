"""
Seat management for train bookings with complex rules.
"""

from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import logging
from typing import List, Tuple, Optional, Dict
from django.db.models import Q

logger = logging.getLogger(__name__)


class TrainSeatManager:
    """Manage train seat booking with RAC and Waitlist support."""
    
    @staticmethod
    @transaction.atomic
    def book_seats(
        train_id: str,
        coach_type_id: str,
        from_stop_id: str,
        to_stop_id: str,
        travel_date: datetime.date,
        seat_numbers: List[str],
        quota: str = 'GENERAL'
    ) -> Tuple[bool, Dict, str]:
        """
        Book train seats with journey-based availability check.
        Returns: (success, booking_data, error_message)
        """
        from .models import Train, Coach, Seat, TrainStop, CoachType
        
        try:
            train = Train.objects.select_for_update().get(id=train_id)
            from_stop = TrainStop.objects.get(id=from_stop_id)
            to_stop = TrainStop.objects.get(id=to_stop_id)
            coach_type = CoachType.objects.get(id=coach_type_id)
            
            # Validate travel date
            if travel_date < timezone.now().date():
                return False, {}, "Travel date cannot be in the past"
            
            # Check if train runs on that day
            day_of_week = travel_date.weekday()  # 0=Monday, 6=Sunday
            # Convert to Sunday-based index (0=Sunday)
            day_index = (day_of_week + 1) % 7
            if not train.runs_on_day(day_index):
                return False, {}, f"Train {train.train_number} doesn't run on {travel_date.strftime('%A')}"
            
            # Find available coach of specified type
            coach = Coach.objects.filter(
                train=train,
                coach_type=coach_type,
                status='AVAILABLE'
            ).first()
            
            if not coach:
                return False, {}, f"No available {coach_type.name} coach"
            
            # Check seat availability for the journey segment
            available_seats = TrainSeatManager.get_available_seats_for_journey(
                coach.id, from_stop.sequence, to_stop.sequence, travel_date, quota
            )
            
            # Check if all requested seats are available
            unavailable_seats = set(seat_numbers) - set(available_seats)
            if unavailable_seats:
                return False, {}, f"Seats {unavailable_seats} are not available for this journey"
            
            # Book seats
            seats = Seat.objects.select_for_update().filter(
                coach=coach,
                seat_number__in=seat_numbers,
                is_booked=False,
                is_blocked=False
            )
            
            seats.update(is_booked=True)
            
            # Update coach availability
            coach.update_available_seats()
            
            # Calculate fare
            fare_details = TrainSeatManager.calculate_journey_fare(
                train_id, coach_type_id, from_stop_id, to_stop_id, quota
            )
            
            booking_data = {
                'train_number': train.train_number,
                'train_name': train.train_name,
                'from_station': from_stop.station_name,
                'to_station': to_stop.station_name,
                'travel_date': travel_date,
                'coach_type': coach_type.name,
                'coach_number': coach.coach_number,
                'seats': seat_numbers,
                'quota': quota,
                'fare_details': fare_details,
                'total_amount': fare_details['total_amount'],
            }
            
            logger.info(f"Booked seats {seat_numbers} on train {train.train_number}")
            return True, booking_data, ""
            
        except Train.DoesNotExist:
            return False, {}, "Train not found"
        except CoachType.DoesNotExist:
            return False, {}, "Coach type not found"
        except Exception as e:
            logger.error(f"Error booking train seats: {str(e)}")
            return False, {}, f"Booking failed: {str(e)}"
    
    @staticmethod
    def get_available_seats_for_journey(
        coach_id: str,
        from_sequence: int,
        to_sequence: int,
        travel_date: datetime.date,
        quota: str
    ) -> List[str]:
        """Get seats available for specific journey segment."""
        from .models import Seat, TrainBooking
        
        try:
            # Get all seats in coach
            all_seats = Seat.objects.filter(coach_id=coach_id)
            available_seats = []
            
            for seat in all_seats:
                if seat.is_booked or seat.is_blocked:
                    continue
                
                # Check if seat is booked for overlapping journey
                overlapping_bookings = TrainBooking.objects.filter(
                    seats_booked__contains=[seat.seat_number],
                    travel_date=travel_date,
                    status__in=['CONFIRMED', 'RAC', 'PENDING']
                )
                
                is_available = True
                for booking in overlapping_bookings:
                    # Check if journeys overlap
                    if (booking.from_station.sequence < to_sequence and 
                        booking.to_station.sequence > from_sequence):
                        is_available = False
                        break
                
                if is_available:
                    available_seats.append(seat.seat_number)
            
            return available_seats
            
        except Exception as e:
            logger.error(f"Error getting available seats: {str(e)}")
            return []
    
    @staticmethod
    def calculate_journey_fare(
        train_id: str,
        coach_type_id: str,
        from_stop_id: str,
        to_stop_id: str,
        quota: str
    ) -> Dict:
        """Calculate fare for train journey."""
        from .models import Train, CoachType, TrainStop, FareRule
        
        try:
            train = Train.objects.get(id=train_id)
            coach_type = CoachType.objects.get(id=coach_type_id)
            from_stop = TrainStop.objects.get(id=from_stop_id)
            to_stop = TrainStop.objects.get(id=to_stop_id)
            
            # Calculate distance
            distance = to_stop.distance_from_source - from_stop.distance_from_source
            
            # Find applicable fare rule
            today = timezone.now().date()
            fare_rule = FareRule.objects.filter(
                coach_type=coach_type,
                from_date__lte=today,
                min_distance__lte=distance
            ).order_by('-from_date').first()
            
            if fare_rule:
                fare_per_km = fare_rule.fare_per_km
            else:
                fare_per_km = coach_type.base_fare_per_km
            
            # Base fare
            base_fare = distance * fare_per_km
            
            # Add charges
            reservation_charge = coach_type.reservation_charge
            superfast_charge = coach_type.superfast_charge if train.train_type == 'SUPERFAST' else Decimal('0.00')
            
            # Tatkal charge
            tatkal_charge = Decimal('0.00')
            if quota in ['TATKAL', 'PREMIUM_TATKAL']:
                days_before = (datetime.combine(today, datetime.min.time()).date() - today).days
                
                # Tatkal booking opens 1 day before journey (for AC) and 2 days before (for non-AC)
                if coach_type.coach_class in ['FIRST_AC', 'SECOND_AC', 'THIRD_AC', 'AC_CHAIR']:
                    if days_before <= 1:  # AC classes: 1 day before
                        if quota == 'TATKAL':
                            tatkal_charge = base_fare * Decimal('0.10')
                        else:
                            tatkal_charge = base_fare * Decimal('0.30')
                else:
                    if days_before <= 2:  # Non-AC classes: 2 days before
                        if quota == 'TATKAL':
                            tatkal_charge = base_fare * Decimal('0.10')
                        else:
                            tatkal_charge = base_fare * Decimal('0.30')
            
            # Service tax
            service_tax = (base_fare + reservation_charge + superfast_charge + tatkal_charge) * \
                         (coach_type.service_tax_percentage / 100)
            
            total_amount = base_fare + reservation_charge + superfast_charge + tatkal_charge + service_tax
            
            return {
                'distance_km': distance,
                'base_fare': base_fare,
                'reservation_charge': reservation_charge,
                'superfast_charge': superfast_charge,
                'tatkal_charge': tatkal_charge,
                'service_tax': service_tax,
                'total_amount': total_amount,
            }
            
        except Exception as e:
            logger.error(f"Error calculating fare: {str(e)}")
            return {
                'distance_km': 0,
                'base_fare': Decimal('0.00'),
                'reservation_charge': Decimal('0.00'),
                'superfast_charge': Decimal('0.00'),
                'tatkal_charge': Decimal('0.00'),
                'service_tax': Decimal('0.00'),
                'total_amount': Decimal('0.00'),
            }
    
    @staticmethod
    @transaction.atomic
    def check_rac_or_waitlist(
        train_id: str,
        coach_type_id: str,
        from_stop_id: str,
        to_stop_id: str,
        travel_date: datetime.date,
        num_passengers: int,
        quota: str
    ) -> Tuple[str, int, str]:
        """
        Check RAC/Waitlist status.
        Returns: (status, position, message)
        """
        from .models import TrainBooking
        
        try:
            # Get confirmed bookings for this journey
            confirmed_bookings = TrainBooking.objects.filter(
                train_id=train_id,
                coach_type_id=coach_type_id,
                from_station_id=from_stop_id,
                to_station_id=to_stop_id,
                travel_date=travel_date,
                quota=quota,
                status='CONFIRMED'
            ).count()
            
            # Get RAC bookings
            rac_bookings = TrainBooking.objects.filter(
                train_id=train_id,
                coach_type_id=coach_type_id,
                from_station_id=from_stop_id,
                to_station_id=to_stop_id,
                travel_date=travel_date,
                quota=quota,
                status='RAC'
            ).count()
            
            # Get waitlist bookings
            waitlist_bookings = TrainBooking.objects.filter(
                train_id=train_id,
                coach_type_id=coach_type_id,
                from_station_id=from_stop_id,
                to_station_id=to_stop_id,
                travel_date=travel_date,
                quota=quota,
                status='WAITLIST'
            ).count()
            
            # Assume coach capacity (simplified)
            coach_capacity = 72  # Typical coach capacity
            rac_limit = 20  # RAC limit per coach
            waitlist_limit = 50  # Waitlist limit
            
            available_confirmed = coach_capacity - confirmed_bookings
            
            if available_confirmed >= num_passengers:
                return "CONFIRMED", 0, "Seats available for confirmation"
            elif available_confirmed + (rac_limit - rac_bookings) >= num_passengers:
                rac_position = rac_bookings + 1
                return "RAC", rac_position, f"RAC position {rac_position}"
            elif available_confirmed + rac_limit + (waitlist_limit - waitlist_bookings) >= num_passengers:
                waitlist_position = waitlist_bookings + 1
                return "WAITLIST", waitlist_position, f"Waitlist position {waitlist_position}"
            else:
                return "NOT_AVAILABLE", 0, "No seats available"
            
        except Exception as e:
            logger.error(f"Error checking RAC/Waitlist: {str(e)}")
            return "ERROR", 0, str(e)


class TrainAvailabilityManager:
    """Manage train seat availability and predictions."""
    
    @staticmethod
    def get_availability_prediction(
        train_id: str,
        coach_type_id: str,
        from_stop_id: str,
        to_stop_id: str,
        travel_date: datetime.date,
        booking_date: datetime.date = None
    ) -> Dict:
        """Predict availability based on historical data."""
        if booking_date is None:
            booking_date = timezone.now().date()
        
        days_before = (travel_date - booking_date).days
        
        # Simplified prediction logic
        if days_before >= 30:
            probability = 0.95  # High probability 30+ days before
        elif days_before >= 15:
            probability = 0.85  # Good probability 15-29 days before
        elif days_before >= 7:
            probability = 0.70  # Moderate probability 7-14 days before
        elif days_before >= 3:
            probability = 0.40  # Low probability 3-6 days before
        elif days_before >= 1:
            probability = 0.20  # Very low probability 1-2 days before
        else:
            probability = 0.05  # Almost no chance on same day
        
        return {
            'days_before': days_before,
            'probability': probability,
            'prediction': 'HIGH' if probability > 0.7 else 'MEDIUM' if probability > 0.4 else 'LOW',
            'recommendation': TrainAvailabilityManager.get_recommendation(probability, days_before)
        }
    
    @staticmethod
    def get_recommendation(probability: float, days_before: int) -> str:
        """Get recommendation based on availability probability."""
        if probability > 0.8:
            return "Book now - High availability"
        elif probability > 0.6:
            return "Book soon - Good availability"
        elif probability > 0.4:
            return "Consider booking - Limited availability"
        elif probability > 0.2:
            return "Try Tatkal quota - Very limited availability"
        else:
            return "Consider alternative train/date - No availability"
    
    @staticmethod
    def get_alternative_trains(
        from_station: str,
        to_station: str,
        travel_date: datetime.date,
        preferred_time: str = None
    ) -> List[Dict]:
        """Get alternative train options."""
        from .models import Train, TrainStop
        
        try:
            trains = Train.objects.filter(
                Q(stops__station_name__icontains=from_station) &
                Q(stops__station_name__icontains=to_station),
                status='ACTIVE'
            ).distinct()

            
            alternatives = []
            for train in trains:
                # Get stops for this train
                from_stop = train.stops.filter(station_name__icontains=from_station).first()
                to_stop = train.stops.filter(station_name__icontains=to_station).first()
                
                if from_stop and to_stop and from_stop.sequence < to_stop.sequence:
                    # Check if train runs on travel date
                    day_of_week = travel_date.weekday()
                    day_index = (day_of_week + 1) % 7
                    
                    if train.runs_on_day(day_index):
                        alternatives.append({
                            'train_number': train.train_number,
                            'train_name': train.train_name,
                            'train_type': train.train_type,
                            'departure_time': from_stop.departure_time,
                            'arrival_time': to_stop.arrival_time,
                            'duration_hours': ((to_stop.distance_from_source - from_stop.distance_from_source) / 50),
                            'distance_km': to_stop.distance_from_source - from_stop.distance_from_source,
                        })
            
            # Sort by departure time
            alternatives.sort(key=lambda x: x['departure_time'] if x['departure_time'] else datetime.max.time())
            
            return alternatives[:5]  # Return top 5 alternatives
            
        except Exception as e:
            logger.error(f"Error getting alternative trains: {str(e)}")
            return []
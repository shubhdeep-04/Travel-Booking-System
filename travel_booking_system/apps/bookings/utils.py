"""
Utilities for booking operations.
"""

from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import logging
from typing import Dict, List, Tuple, Optional
import uuid

logger = logging.getLogger(__name__)


class BookingManager:
    """Manage booking operations across all services."""
    
    @staticmethod
    @transaction.atomic
    def create_booking(
        user,
        service_type: str,
        service_id: str,
        check_in_date: datetime.date = None,
        check_out_date: datetime.date = None,
        travel_date: datetime.date = None,
        quantity: int = 1,
        adults: int = 1,
        children: int = 0,
        base_amount: Decimal = None,
        tax_amount: Decimal = Decimal('0.00'),
        discount_amount: Decimal = Decimal('0.00'),
        contact_name: str = None,
        contact_email: str = None,
        contact_phone: str = None,
        special_requests: str = '',
        metadata: Dict = None
    ) -> Tuple[bool, Optional['Booking'], str]:
        """
        Create a unified booking for any service.
        Returns: (success, booking, error_message)
        """
        from .models import Booking
        
        try:
            # Validate dates
            if check_in_date and check_out_date:
                if check_out_date <= check_in_date:
                    return False, None, "Check-out date must be after check-in date"
            
            # Calculate total amount
            total_amount = (base_amount or Decimal('0.00')) + tax_amount - discount_amount
            
            if total_amount <= 0:
                return False, None, "Total amount must be greater than zero"
            
            # Use user info if contact info not provided
            if not contact_name:
                contact_name = user.get_full_name() or user.username
            if not contact_email:
                contact_email = user.email
            
            # Create booking
            booking = Booking.objects.create(
                user=user,
                service_type=service_type,
                service_id=service_id,
                check_in_date=check_in_date,
                check_out_date=check_out_date,
                travel_date=travel_date,
                quantity=quantity,
                adults=adults,
                children=children,
                base_amount=base_amount or Decimal('0.00'),
                tax_amount=tax_amount,
                discount_amount=discount_amount,
                total_amount=total_amount,
                status=Booking.Status.PENDING,
                contact_name=contact_name,
                contact_email=contact_email,
                contact_phone=contact_phone or '',
                special_requests=special_requests,
                metadata=metadata or {}
            )
            
            # Create initial history entry
            from .models import BookingHistory
            BookingHistory.objects.create(
                booking=booking,
                new_status=Booking.Status.PENDING,
                notes="Booking created",
                metadata={'created_by': 'system'}
            )
            
            logger.info(f"Booking created: {booking.booking_reference} for user {user.id}")
            return True, booking, ""
            
        except Exception as e:
            logger.error(f"Error creating booking: {str(e)}")
            return False, None, f"Booking creation failed: {str(e)}"
    
    @staticmethod
    @transaction.atomic
    def confirm_booking(booking_id: str) -> Tuple[bool, str]:
        """Confirm a pending booking."""
        from .models import Booking, BookingHistory
        
        try:
            booking = Booking.objects.select_for_update().get(id=booking_id)
            
            if booking.status != Booking.Status.PENDING:
                return False, f"Booking is not in pending state. Current status: {booking.status}"
            
            booking.status = Booking.Status.CONFIRMED
            booking.save()
            
            # Create history entry
            BookingHistory.objects.create(
                booking=booking,
                old_status=Booking.Status.PENDING,
                new_status=Booking.Status.CONFIRMED,
                notes="Booking confirmed",
                metadata={'confirmed_by': 'system'}
            )
            
            # Send confirmation email (in production)
            # send_booking_confirmation_email(booking)
            
            logger.info(f"Booking confirmed: {booking.booking_reference}")
            return True, "Booking confirmed successfully"
            
        except Booking.DoesNotExist:
            return False, "Booking not found"
        except Exception as e:
            logger.error(f"Error confirming booking: {str(e)}")
            return False, f"Confirmation failed: {str(e)}"
    
    @staticmethod
    def calculate_refund_amount(
        booking,
        cancellation_date: datetime = None
    ) -> Decimal:
        """Calculate refund amount based on cancellation policy."""
        if cancellation_date is None:
            cancellation_date = timezone.now()
        
        # Determine relevant date for cancellation policy
        relevant_date = None
        if booking.check_in_date:
            relevant_date = booking.check_in_date
        elif booking.travel_date:
            relevant_date = booking.travel_date
        else:
            relevant_date = booking.booking_date.date()
        
        # Calculate time difference
        if isinstance(relevant_date, datetime.date):
            relevant_datetime = datetime.combine(relevant_date, datetime.min.time())
        else:
            relevant_datetime = relevant_date
        
        time_diff = relevant_datetime - cancellation_date
        
        # Define cancellation policies per service type
        policies = {
            'HOTEL': {
                'free_cancellation_hours': 48,  # 48 hours before check-in
                'partial_refund_hours': 24,     # 24-48 hours: 50% refund
                'no_refund_hours': 0,           # Less than 24 hours: no refund
            },
            'CAR': {
                'free_cancellation_hours': 168,  # 7 days
                'partial_refund_hours': 72,      # 3-7 days: 50% refund
                'no_refund_hours': 24,           # Less than 24 hours: no refund
            },
            'BUS': {
                'free_cancellation_hours': 4,    # 4 hours before departure
                'partial_refund_hours': 0,       # No partial refund
                'no_refund_hours': 0,           # No refund within 4 hours
            },
            'TRAIN': {
                'free_cancellation_hours': 48,   # 2 days
                'partial_refund_hours': 24,      # 1-2 days: 50% refund
                'no_refund_hours': 0,           # Less than 24 hours: no refund
            },
        }
        
        policy = policies.get(booking.service_type, {})
        hours_before = time_diff.total_seconds() / 3600
        
        if hours_before >= policy.get('free_cancellation_hours', 0):
            return booking.total_amount  # Full refund
        elif hours_before >= policy.get('partial_refund_hours', 0):
            return booking.total_amount * Decimal('0.5')  # 50% refund
        else:
            return Decimal('0.00')  # No refund
    
    @staticmethod
    def get_upcoming_bookings(user, limit: int = 10) -> List:
        """Get user's upcoming bookings."""
        from .models import Booking
        
        now = timezone.now().date()
        
        upcoming = Booking.objects.filter(
            user=user,
            status=Booking.Status.CONFIRMED
        ).filter(
            Q(check_in_date__gte=now) |
            Q(travel_date__gte=now)
        ).order_by(
            'check_in_date', 'travel_date'
        )[:limit]
        
        return upcoming
    
    @staticmethod
    def generate_invoice_data(booking) -> Dict:
        """Generate invoice data for a booking."""
        from django.conf import settings
        
        invoice_data = {
            'invoice_number': f"INV-{booking.booking_reference}",
            'invoice_date': timezone.now().strftime('%Y-%m-%d'),
            'booking_reference': booking.booking_reference,
            'customer': {
                'name': booking.contact_name,
                'email': booking.contact_email,
                'phone': booking.contact_phone,
            },
            'service_details': {
                'type': booking.get_service_type_display(),
                'name': booking.service_name,
                'dates': {
                    'check_in': booking.check_in_date,
                    'check_out': booking.check_out_date,
                    'travel': booking.travel_date,
                },
                'details': booking.get_service_details(),
            },
            'breakdown': {
                'base_amount': float(booking.base_amount),
                'tax_amount': float(booking.tax_amount),
                'discount_amount': float(booking.discount_amount),
                'total_amount': float(booking.total_amount),
            },
            'company': {
                'name': settings.COMPANY_NAME if hasattr(settings, 'COMPANY_NAME') else 'Travel Booking System',
                'address': settings.COMPANY_ADDRESS if hasattr(settings, 'COMPANY_ADDRESS') else '',
                'phone': settings.COMPANY_PHONE if hasattr(settings, 'COMPANY_PHONE') else '',
                'email': settings.COMPANY_EMAIL if hasattr(settings, 'COMPANY_EMAIL') else '',
            }
        }
        
        return invoice_data


class BookingAnalytics:
    """Analytics for booking data."""
    
    @staticmethod
    def get_user_booking_stats(user, days: int = 30) -> Dict:
        """Get booking statistics for a user."""
        from .models import Booking
        from django.db.models import Count, Sum, Avg
        
        start_date = timezone.now().date() - timedelta(days=days)
        
        bookings = Booking.objects.filter(
            user=user,
            booking_date__date__gte=start_date
        )
        
        stats = bookings.aggregate(
            total_bookings=Count('id'),
            total_spent=Sum('total_amount'),
            avg_booking_value=Avg('total_amount'),
            confirmed_bookings=Count('id', filter=models.Q(status='CONFIRMED')),
            cancelled_bookings=Count('id', filter=models.Q(status='CANCELLED')),
        )
        
        # Service type breakdown
        service_breakdown = list(bookings.values('service_type').annotate(
            count=Count('id'),
            amount=Sum('total_amount')
        ).order_by('-count'))
        
        return {
            'period': {
                'start': start_date,
                'end': timezone.now().date(),
                'days': days,
            },
            'summary': stats,
            'service_breakdown': service_breakdown,
        }
    
    @staticmethod
    def get_admin_analytics(start_date: datetime.date, end_date: datetime.date) -> Dict:
        """Get booking analytics for admin dashboard."""
        from .models import Booking
        from django.db.models import Count, Sum, Avg
        
        bookings = Booking.objects.filter(
            booking_date__date__range=[start_date, end_date]
        )
        
        # Overall statistics
        overall = bookings.aggregate(
            total_bookings=Count('id'),
            total_revenue=Sum('total_amount'),
            avg_booking_value=Avg('total_amount'),
            confirmed_rate=Count('id', filter=models.Q(status='CONFIRMED')) * 100.0 / Count('id') if Count('id') > 0 else 0,
        )
        
        # Daily trends
        daily_trends = list(bookings.extra(
            select={'day': 'DATE(booking_date)'}
        ).values('day').annotate(
            bookings=Count('id'),
            revenue=Sum('total_amount')
        ).order_by('day'))
        
        # Service type analysis
        service_analysis = list(bookings.values('service_type').annotate(
            bookings=Count('id'),
            revenue=Sum('total_amount'),
            avg_value=Avg('total_amount')
        ).order_by('-revenue'))
        
        # Status breakdown
        status_breakdown = list(bookings.values('status').annotate(
            count=Count('id'),
            percentage=Count('id') * 100.0 / bookings.count()
        ).order_by('-count'))
        
        return {
            'period': {
                'start': start_date,
                'end': end_date,
            },
            'overall': overall,
            'daily_trends': daily_trends,
            'service_analysis': service_analysis,
            'status_breakdown': status_breakdown,
        }
    
    @staticmethod
    def predict_revenue(
        start_date: datetime.date,
        end_date: datetime.date,
        historical_days: int = 90
    ) -> Dict:
        """Predict revenue based on historical data."""
        from .models import Booking
        from django.db.models import Sum, Avg
        
        # Get historical data
        history_start = start_date - timedelta(days=historical_days)
        historical_bookings = Booking.objects.filter(
            booking_date__date__range=[history_start, start_date - timedelta(days=1)],
            status__in=['CONFIRMED', 'COMPLETED']
        )
        
        # Calculate average daily revenue
        avg_daily_revenue = historical_bookings.aggregate(
            avg=Avg('total_amount')
        )['avg'] or Decimal('0.00')
        
        # Calculate predicted revenue
        days = (end_date - start_date).days + 1
        predicted_revenue = avg_daily_revenue * days
        
        # Get confidence interval (simplified)
        # In production, use more sophisticated forecasting
        confidence_interval = {
            'lower': predicted_revenue * Decimal('0.8'),  # -20%
            'upper': predicted_revenue * Decimal('1.2'),  # +20%
        }
        
        return {
            'prediction_period': {
                'start': start_date,
                'end': end_date,
                'days': days,
            },
            'predicted_revenue': predicted_revenue,
            'confidence_interval': confidence_interval,
            'historical_data_days': historical_days,
            'avg_daily_revenue': avg_daily_revenue,
        }


class BookingValidator:
    """Validate booking data and constraints."""
    
    @staticmethod
    def validate_booking_dates(
        service_type: str,
        check_in_date: datetime.date = None,
        check_out_date: datetime.date = None,
        travel_date: datetime.date = None
    ) -> Tuple[bool, List[str]]:
        """Validate booking dates based on service type."""
        errors = []
        today = timezone.now().date()
        
        if service_type == 'HOTEL':
            if not check_in_date or not check_out_date:
                errors.append("Both check-in and check-out dates are required for hotel bookings")
            else:
                if check_in_date < today:
                    errors.append("Check-in date cannot be in the past")
                if check_out_date <= check_in_date:
                    errors.append("Check-out date must be after check-in date")
                if (check_out_date - check_in_date).days > 30:
                    errors.append("Maximum stay is 30 days")
        
        elif service_type == 'CAR':
            if not check_in_date or not check_out_date:
                errors.append("Both pick-up and drop-off dates are required for car rentals")
            else:
                if check_in_date < today:
                    errors.append("Pick-up date cannot be in the past")
                if check_out_date <= check_in_date:
                    errors.append("Drop-off date must be after pick-up date")
                if (check_out_date - check_in_date).days > 90:
                    errors.append("Maximum rental period is 90 days")
        
        elif service_type in ['BUS', 'TRAIN']:
            if not travel_date:
                errors.append("Travel date is required")
            else:
                if travel_date < today:
                    errors.append("Travel date cannot be in the past")
                if travel_date > today + timedelta(days=120):
                    errors.append("Maximum advance booking is 120 days")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_passenger_count(
        service_type: str,
        adults: int,
        children: int,
        quantity: int = 1
    ) -> Tuple[bool, List[str]]:
        """Validate passenger/occupant counts."""
        errors = []
        total_passengers = adults + children
        
        if service_type == 'HOTEL':
            if adults < 1:
                errors.append("At least one adult is required")
            if total_passengers > quantity * 4:  # Assuming max 4 per room
                errors.append("Maximum 4 guests per room")
        
        elif service_type == 'CAR':
            if adults < 1:
                errors.append("At least one adult driver is required")
            if adults > quantity * 2:  # Assuming 2 drivers per car max
                errors.append("Maximum 2 drivers per car")
        
        elif service_type in ['BUS', 'TRAIN']:
            if adults < 1:
                errors.append("At least one adult passenger is required")
            if total_passengers > 6:  # Max 6 tickets per booking
                errors.append("Maximum 6 passengers per booking")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def check_service_availability(
        service_type: str,
        service_id: str,
        check_in_date: datetime.date = None,
        check_out_date: datetime.date = None,
        travel_date: datetime.date = None,
        quantity: int = 1
    ) -> Tuple[bool, str]:
        """
        Check service availability.
        In production, this would integrate with each service's availability system.
        """
        # This is a simplified version
        # In production, you would call the respective service's availability check
        
        try:
            if service_type == 'HOTEL':
                from apps.hotels.models import HotelRoom
                room = HotelRoom.objects.get(id=service_id)
                if not room.is_available:
                    return False, "Room is not available"
                if room.available_rooms < quantity:
                    return False, f"Only {room.available_rooms} room(s) available"
                
                # Check date availability (simplified)
                # In production, check against existing bookings
                return True, "Available"
            
            elif service_type == 'CAR':
                from apps.cars.models import Car
                car = Car.objects.get(id=service_id)
                if car.status != 'AVAILABLE':
                    return False, f"Car is {car.get_status_display()}"
                
                # Check date availability (simplified)
                return True, "Available"
            
            elif service_type == 'BUS':
                from apps.buses.models import Bus
                bus = Bus.objects.get(id=service_id)
                if bus.status != 'ACTIVE':
                    return False, f"Bus is {bus.get_status_display()}"
                
                # Check seat availability (simplified)
                available_seats = bus.available_seats
                if available_seats < quantity:
                    return False, f"Only {available_seats} seat(s) available"
                
                return True, "Available"
            
            elif service_type == 'TRAIN':
                from apps.trains.models import Train
                train = Train.objects.get(id=service_id)
                if train.status != 'ACTIVE':
                    return False, f"Train is {train.get_status_display()}"
                
                # Check if train runs on travel date
                if travel_date:
                    day_of_week = travel_date.weekday()
                    day_index = (day_of_week + 1) % 7
                    if not train.runs_on_day(day_index):
                        return False, f"Train doesn't run on {travel_date.strftime('%A')}"
                
                return True, "Available"
            
            return False, "Unknown service type"
            
        except Exception as e:
            logger.error(f"Error checking availability: {str(e)}")
            return False, f"Availability check failed: {str(e)}"
"""
Bus Ticket Booking Models for Travel Booking System.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid

class BusOperator(models.Model):
    """Bus operator/company."""
    name = models.CharField(_('operator name'), max_length=200, unique=True)
    code = models.CharField(_('operator code'), max_length=20, unique=True)
    description = models.TextField(_('description'), blank=True)
    logo = models.ImageField(
        _('logo'),
        upload_to='buses/operators/',
        blank=True,
        null=True
    )
    contact_number = models.CharField(_('contact number'), max_length=20, blank=True)
    email = models.EmailField(_('email'), blank=True)
    website = models.URLField(_('website'), blank=True)
    rating = models.DecimalField(
        _('rating'),
        max_digits=3,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    
    class Meta:
        verbose_name = _('Bus Operator')
        verbose_name_plural = _('Bus Operators')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class BusType(models.Model):
    """Type of bus (AC, Non-AC, Sleeper, etc.)."""
    name = models.CharField(_('bus type'), max_length=100, unique=True)
    description = models.TextField(_('description'), blank=True)
    icon = models.CharField(
        _('icon'),
        max_length=50,
        blank=True,
        help_text=_('Font Awesome icon class')
    )
    
    class Meta:
        verbose_name = _('Bus Type')
        verbose_name_plural = _('Bus Types')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Bus(models.Model):
    """Bus model for ticket booking."""
    
    class BusStatus(models.TextChoices):
        ACTIVE = 'ACTIVE', _('Active')
        INACTIVE = 'INACTIVE', _('Inactive')
        MAINTENANCE = 'MAINTENANCE', _('Under Maintenance')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bus_number = models.CharField(_('bus number'), max_length=50, unique=True)
    operator = models.ForeignKey(
        BusOperator,
        on_delete=models.PROTECT,
        related_name='buses'
    )
    bus_type = models.ForeignKey(
        BusType,
        on_delete=models.PROTECT,
        related_name='buses'
    )
    
    # Route Information
    route_from = models.CharField(_('from'), max_length=200)
    route_to = models.CharField(_('to'), max_length=200)
    via_cities = models.TextField(
        _('via cities'),
        blank=True,
        help_text=_('Comma separated list of intermediate cities')
    )
    distance_km = models.PositiveIntegerField(
        _('distance (km)'),
        null=True,
        blank=True
    )
    
    # Schedule
    departure_time = models.TimeField(_('departure time'))
    arrival_time = models.TimeField(_('arrival time'))
    duration_hours = models.DecimalField(
        _('duration (hours)'),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Seat Configuration
    total_seats = models.PositiveIntegerField(_('total seats'), default=40)
    seats_per_row = models.PositiveIntegerField(_('seats per row'), default=4)
    seat_layout = models.JSONField(
        _('seat layout'),
        default=list,
        help_text=_('JSON array representing seat layout (e.g., [1,2] for 1+2 layout)')
    )
    
    # Amenities
    has_ac = models.BooleanField(_('has AC'), default=False)
    has_wifi = models.BooleanField(_('has WiFi'), default=False)
    has_charging = models.BooleanField(_('has charging'), default=False)
    has_toilet = models.BooleanField(_('has toilet'), default=False)
    has_tv = models.BooleanField(_('has TV'), default=False)
    is_sleeper = models.BooleanField(_('sleeper bus'), default=False)
    
    # Fare Information
    base_fare = models.DecimalField(
        _('base fare'),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    tax_percentage = models.DecimalField(
        _('tax percentage'),
        max_digits=5,
        decimal_places=2,
        default=5.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # Cancellation Policy
    cancellation_before_hours = models.PositiveIntegerField(
        _('free cancellation before hours'),
        default=4,
        help_text=_('Hours before departure for free cancellation')
    )
    cancellation_charge_percentage = models.DecimalField(
        _('cancellation charge percentage'),
        max_digits=5,
        decimal_places=2,
        default=10.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # Status
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=BusStatus.choices,
        default=BusStatus.ACTIVE
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['departure_time', 'bus_number']
        verbose_name = _('Bus')
        verbose_name_plural = _('Buses')
        indexes = [
            models.Index(fields=['route_from', 'route_to', 'departure_time']),
            models.Index(fields=['operator', 'bus_type']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.operator.name} - {self.bus_number} ({self.route_from} to {self.route_to})"
    
    @property
    def route_name(self):
        return f"{self.route_from} → {self.route_to}"
    
    @property
    def final_fare(self):
        """Calculate fare including tax."""
        tax_amount = (self.base_fare * self.tax_percentage) / 100
        return self.base_fare + tax_amount
    
    @property
    def available_seats(self):
        """Get count of available seats."""
        return self.seats.filter(is_booked=False).count()
    
    @property
    def is_full(self):
        """Check if bus is fully booked."""
        return self.available_seats == 0
    
    def get_available_seats(self):
        """Get list of available seat numbers."""
        return list(self.seats.filter(is_booked=False).values_list('seat_number', flat=True))
    
    def is_running_on_day(self, date):
        """Check if bus runs on specific date."""
        # For now, assume bus runs daily
        # In production, you'd have a schedule model
        return True


class BusSchedule(models.Model):
    """Schedule for specific dates (for daily/weekly variations)."""
    
    class DaysOfWeek(models.TextChoices):
        MONDAY = 'MON', _('Monday')
        TUESDAY = 'TUE', _('Tuesday')
        WEDNESDAY = 'WED', _('Wednesday')
        THURSDAY = 'THU', _('Thursday')
        FRIDAY = 'FRI', _('Friday')
        SATURDAY = 'SAT', _('Saturday')
        SUNDAY = 'SUN', _('Sunday')
    
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name='schedules')
    days = models.CharField(
        _('days of week'),
        max_length=50,
        help_text=_('Comma separated days: MON,TUE,WED,THU,FRI,SAT,SUN')
    )
    effective_from = models.DateField(_('effective from'))
    effective_to = models.DateField(_('effective to'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('Bus Schedule')
        verbose_name_plural = _('Bus Schedules')
    
    def __str__(self):
        return f"Schedule for {self.bus.bus_number}"


class BusSeat(models.Model):
    """Individual seat in a bus."""
    
    class SeatType(models.TextChoices):
        NORMAL = 'NORMAL', _('Normal')
        WINDOW = 'WINDOW', _('Window')
        AISLE = 'AISLE', _('Aisle')
        SLEEPER = 'SLEEPER', _('Sleeper')
    
    class SeatGender(models.TextChoices):
        ANY = 'ANY', _('Any')
        MALE = 'MALE', _('Male Only')
        FEMALE = 'FEMALE', _('Female Only')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name='seats')
    seat_number = models.CharField(_('seat number'), max_length=10)
    seat_type = models.CharField(
        _('seat type'),
        max_length=20,
        choices=SeatType.choices,
        default=SeatType.NORMAL
    )
    seat_gender = models.CharField(
        _('seat gender'),
        max_length=10,
        choices=SeatGender.choices,
        default=SeatGender.ANY
    )
    row_number = models.PositiveIntegerField(_('row number'))
    column_number = models.PositiveIntegerField(_('column number'))
    
    # Pricing (can be different from base fare)
    fare_adjustment = models.DecimalField(
        _('fare adjustment'),
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text=_('Additional amount for this seat (can be negative)')
    )
    
    # Status
    is_booked = models.BooleanField(_('is booked'), default=False)
    is_blocked = models.BooleanField(_('is blocked'), default=False)
    block_reason = models.CharField(_('block reason'), max_length=200, blank=True)
    
    # Features
    is_emergency_exit = models.BooleanField(_('emergency exit'), default=False)
    is_near_toilet = models.BooleanField(_('near toilet'), default=False)
    
    class Meta:
        ordering = ['row_number', 'column_number']
        verbose_name = _('Bus Seat')
        verbose_name_plural = _('Bus Seats')
        unique_together = ['bus', 'seat_number']
        indexes = [
            models.Index(fields=['bus', 'is_booked', 'is_blocked']),
            models.Index(fields=['seat_type']),
        ]
    
    def __str__(self):
        return f"Seat {self.seat_number} - {self.bus.bus_number}"
    
    @property
    def final_fare(self):
        """Calculate final fare for this seat."""
        return self.bus.final_fare + self.fare_adjustment
    
    @property
    def is_available(self):
        """Check if seat is available for booking."""
        return not (self.is_booked or self.is_blocked)
    
    @property
    def seat_position(self):
        """Get seat position description."""
        return f"Row {self.row_number}, Seat {self.seat_number}"


class BusBooking(models.Model):
    """Bus ticket booking."""
    
    class BookingStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        CONFIRMED = 'CONFIRMED', _('Confirmed')
        CANCELLED = 'CANCELLED', _('Cancelled')
        NO_SHOW = 'NO_SHOW', _('No Show')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='bus_bookings'
    )
    bus = models.ForeignKey(Bus, on_delete=models.PROTECT, related_name='bookings')
    travel_date = models.DateField(_('travel date'))
    
    # Booking Details
    seats_booked = models.JSONField(
        _('seats booked'),
        default=list,
        help_text=_('List of seat numbers booked')
    )
    total_passengers = models.PositiveIntegerField(_('total passengers'))
    total_amount = models.DecimalField(
        _('total amount'),
        max_digits=10,
        decimal_places=2
    )
    
    # Passenger Information
    passenger_name = models.CharField(_('passenger name'), max_length=200)
    passenger_age = models.PositiveIntegerField(_('passenger age'), null=True, blank=True)
    passenger_gender = models.CharField(
        _('passenger gender'),
        max_length=10,
        choices=[('MALE', 'Male'), ('FEMALE', 'Female'), ('OTHER', 'Other')]
    )
    passenger_phone = models.CharField(_('passenger phone'), max_length=20)
    passenger_email = models.EmailField(_('passenger email'), blank=True)
    
    # Boarding/Dropping Points
    boarding_point = models.CharField(_('boarding point'), max_length=200)
    dropping_point = models.CharField(_('dropping point'), max_length=200)
    
    # Status
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=BookingStatus.choices,
        default=BookingStatus.PENDING
    )
    
    # Cancellation
    cancellation_reason = models.TextField(_('cancellation reason'), blank=True)
    cancellation_charge = models.DecimalField(
        _('cancellation charge'),
        max_digits=10,
        decimal_places=2,
        default=0.00
    )
    cancelled_at = models.DateTimeField(_('cancelled at'), null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Bus Booking')
        verbose_name_plural = _('Bus Bookings')
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['bus', 'travel_date']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Booking {self.id} - {self.bus.bus_number}"
    
    @property
    def pnr_number(self):
        """Generate PNR number."""
        return f"BUS{str(self.id).replace('-', '').upper()[:10]}"
    
    def cancel_booking(self, reason=""):
        """Cancel this booking."""
        from .seat_manager import SeatManager
        
        self.status = self.BookingStatus.CANCELLED
        self.cancellation_reason = reason
        self.cancelled_at = timezone.now()
        
        # Calculate cancellation charge
        hours_before = (self.travel_date - timezone.now().date()).days * 24
        if hours_before < self.bus.cancellation_before_hours:
            self.cancellation_charge = (self.total_amount * self.bus.cancellation_charge_percentage) / 100
        
        self.save()
        
        # Release seats
        SeatManager.release_seats(self.bus, self.seats_booked)


class BusReview(models.Model):
    """Reviews for bus journeys."""
    
    class Rating(models.IntegerChoices):
        ONE = 1, '★'
        TWO = 2, '★★'
        THREE = 3, '★★★'
        FOUR = 4, '★★★★'
        FIVE = 5, '★★★★★'
    
    bus = models.ForeignKey(
        Bus,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='bus_reviews'
    )
    booking = models.ForeignKey(
        BusBooking,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviews'
    )
    rating = models.IntegerField(_('rating'), choices=Rating.choices)
    title = models.CharField(_('review title'), max_length=200)
    comment = models.TextField(_('comment'))
    
    # Review aspects
    cleanliness = models.PositiveIntegerField(
        _('cleanliness'),
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=5
    )
    comfort = models.PositiveIntegerField(
        _('comfort'),
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=5
    )
    punctuality = models.PositiveIntegerField(
        _('punctuality'),
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=5
    )
    staff_behavior = models.PositiveIntegerField(
        _('staff behavior'),
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=5
    )
    value_for_money = models.PositiveIntegerField(
        _('value for money'),
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=5
    )
    
    is_verified = models.BooleanField(_('verified review'), default=False)
    helpful_count = models.PositiveIntegerField(_('helpful count'), default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Bus Review')
        verbose_name_plural = _('Bus Reviews')
        unique_together = ['bus', 'user', 'booking']
        indexes = [
            models.Index(fields=['bus', 'rating']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username}'s review of {self.bus.bus_number}"
    
    @property
    def overall_rating(self):
        """Calculate average of all aspect ratings."""
        aspects = [self.cleanliness, self.comfort, self.punctuality, 
                  self.staff_behavior, self.value_for_money]
        return sum(aspects) / len(aspects)


class BusStop(models.Model):
    """Bus stops along a route."""
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name='stops')
    city = models.CharField(_('city'), max_length=100)
    stop_name = models.CharField(_('stop name'), max_length=200)
    arrival_time = models.TimeField(_('arrival time'), null=True, blank=True)
    departure_time = models.TimeField(_('departure time'), null=True, blank=True)
    sequence = models.PositiveIntegerField(_('sequence'))
    
    class Meta:
        ordering = ['sequence']
        verbose_name = _('Bus Stop')
        verbose_name_plural = _('Bus Stops')
        unique_together = ['bus', 'sequence']
    
    def __str__(self):
        return f"{self.stop_name}, {self.city} - {self.bus.bus_number}"
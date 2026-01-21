"""
Train Ticket Booking Models for Travel Booking System.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid

class Train(models.Model):
    """Train model for ticket booking."""
    
    class TrainType(models.TextChoices):
        EXPRESS = 'EXPRESS', _('Express')
        MAIL = 'MAIL', _('Mail')
        SUPERFAST = 'SUPERFAST', _('Superfast')
        RAJDHANI = 'RAJDHANI', _('Rajdhani')
        SHATABDI = 'SHATABDI', _('Shatabdi')
        DURONTO = 'DURONTO', _('Duronto')
        LOCAL = 'LOCAL', _('Local')
        METRO = 'METRO', _('Metro')
    
    class TrainStatus(models.TextChoices):
        ACTIVE = 'ACTIVE', _('Active')
        INACTIVE = 'INACTIVE', _('Inactive')
        CANCELLED = 'CANCELLED', _('Cancelled')
        DIVERTED = 'DIVERTED', _('Diverted')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    train_number = models.CharField(_('train number'), max_length=20, unique=True)
    train_name = models.CharField(_('train name'), max_length=200)
    train_type = models.CharField(
        _('train type'),
        max_length=20,
        choices=TrainType.choices,
        default=TrainType.EXPRESS
    )
    
    # Route Information
    source_station = models.CharField(_('source station'), max_length=200)
    destination_station = models.CharField(_('destination station'), max_length=200)
    source_station_code = models.CharField(_('source code'), max_length=10)
    destination_station_code = models.CharField(_('destination code'), max_length=10)
    
    # Schedule
    departure_time = models.TimeField(_('departure time'))
    arrival_time = models.TimeField(_('arrival time'))
    running_days = models.CharField(
        _('running days'),
        max_length=50,
        default='1111111',  # 7 digits for Sun-Sat (1=runs, 0=doesn't run)
        help_text=_('7 digits (Sun-Sat), 1=runs, 0=doesn\'t run')
    )
    duration_hours = models.DecimalField(
        _('duration (hours)'),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    distance_km = models.PositiveIntegerField(_('distance (km)'), null=True, blank=True)
    
    # Coach Information
    total_coaches = models.PositiveIntegerField(_('total coaches'), default=20)
    
    # Status
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=TrainStatus.choices,
        default=TrainStatus.ACTIVE
    )
    
    # Additional Information
    has_pantry = models.BooleanField(_('has pantry car'), default=False)
    has_ac = models.BooleanField(_('has AC coaches'), default=True)
    avg_speed_kmph = models.PositiveIntegerField(_('average speed (kmph)'), null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['train_number']
        verbose_name = _('Train')
        verbose_name_plural = _('Trains')
        indexes = [
            models.Index(fields=['train_number', 'status']),
            models.Index(fields=['source_station', 'destination_station']),
            models.Index(fields=['train_type']),
        ]
    
    def __str__(self):
        return f"{self.train_number} - {self.train_name}"
    
    @property
    def route_name(self):
        return f"{self.source_station} → {self.destination_station}"
    
    @property
    def route_code(self):
        return f"{self.source_station_code} → {self.destination_station_code}"
    
    def runs_on_day(self, day_of_week):
        """Check if train runs on specific day of week (0=Sunday, 6=Saturday)."""
        if len(self.running_days) != 7:
            return True  # Default to running every day if not specified
        
        return self.running_days[day_of_week] == '1'


class CoachType(models.Model):
    """Type of coach (AC, Sleeper, General, etc.)."""
    
    class CoachClass(models.TextChoices):
        FIRST_AC = 'FIRST_AC', _('First AC')
        SECOND_AC = 'SECOND_AC', _('Second AC')
        THIRD_AC = 'THIRD_AC', _('Third AC')
        AC_CHAIR = 'AC_CHAIR', _('AC Chair Car')
        SLEEPER = 'SLEEPER', _('Sleeper')
        SECOND_SEATING = 'SECOND_SEATING', _('Second Seating')
        GENERAL = 'GENERAL', _('General')
    
    name = models.CharField(_('coach type'), max_length=100)
    coach_class = models.CharField(
        _('coach class'),
        max_length=20,
        choices=CoachClass.choices,
        unique=True
    )
    description = models.TextField(_('description'), blank=True)
    seat_layout = models.JSONField(
        _('seat layout'),
        default=list,
        help_text=_('JSON array representing seat layout per coach')
    )
    total_seats = models.PositiveIntegerField(_('total seats per coach'), default=72)
    base_fare_per_km = models.DecimalField(
        _('base fare per km'),
        max_digits=8,
        decimal_places=4,
        default=0.50
    )
    reservation_charge = models.DecimalField(
        _('reservation charge'),
        max_digits=10,
        decimal_places=2,
        default=20.00
    )
    superfast_charge = models.DecimalField(
        _('superfast charge'),
        max_digits=10,
        decimal_places=2,
        default=30.00
    )
    service_tax_percentage = models.DecimalField(
        _('service tax percentage'),
        max_digits=5,
        decimal_places=2,
        default=5.00
    )
    
    class Meta:
        verbose_name = _('Coach Type')
        verbose_name_plural = _('Coach Types')
        ordering = ['coach_class']
    
    def __str__(self):
        return f"{self.name} ({self.get_coach_class_display()})"
    
    @property
    def fare_calculation_rate(self):
        """Get total fare calculation rate per km."""
        return self.base_fare_per_km


class Coach(models.Model):
    """Individual coach in a train."""
    
    class CoachStatus(models.TextChoices):
        AVAILABLE = 'AVAILABLE', _('Available')
        MAINTENANCE = 'MAINTENANCE', _('Under Maintenance')
        RESERVED = 'RESERVED', _('Reserved for Special Train')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    train = models.ForeignKey(Train, on_delete=models.CASCADE, related_name='coaches')
    coach_type = models.ForeignKey(CoachType, on_delete=models.PROTECT, related_name='coaches')
    coach_number = models.CharField(_('coach number'), max_length=10)
    coach_position = models.PositiveIntegerField(_('coach position'), help_text=_('Position in train'))
    
    # Seat Configuration
    total_seats = models.PositiveIntegerField(_('total seats'))
    available_seats = models.PositiveIntegerField(_('available seats'), default=0)
    
    # Features
    has_charging = models.BooleanField(_('has charging'), default=False)
    has_led_display = models.BooleanField(_('has LED display'), default=True)
    is_ladies_coach = models.BooleanField(_('ladies coach'), default=False)
    is_senior_citizen_coach = models.BooleanField(_('senior citizen coach'), default=False)
    is_handicapped_friendly = models.BooleanField(_('handicapped friendly'), default=False)
    
    # Status
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=CoachStatus.choices,
        default=CoachStatus.AVAILABLE
    )
    
    class Meta:
        ordering = ['train', 'coach_position']
        verbose_name = _('Coach')
        verbose_name_plural = _('Coaches')
        unique_together = ['train', 'coach_number']
        indexes = [
            models.Index(fields=['train', 'coach_type', 'status']),
            models.Index(fields=['available_seats']),
        ]
    
    def __str__(self):
        return f"{self.coach_number} - {self.train.train_number}"
    
    @property
    def is_full(self):
        return self.available_seats == 0
    
    @property
    def occupancy_rate(self):
        if self.total_seats > 0:
            return ((self.total_seats - self.available_seats) / self.total_seats) * 100
        return 0
    
    def update_available_seats(self):
        """Update available seats count."""
        booked_seats = self.seats.filter(is_booked=True).count()
        self.available_seats = self.total_seats - booked_seats
        self.save(update_fields=['available_seats'])


class Seat(models.Model):
    """Individual seat in a coach."""
    
    class BerthType(models.TextChoices):
        LOWER = 'LOWER', _('Lower')
        MIDDLE = 'MIDDLE', _('Middle')
        UPPER = 'UPPER', _('Upper')
        SIDE_LOWER = 'SIDE_LOWER', _('Side Lower')
        SIDE_UPPER = 'SIDE_UPPER', _('Side Upper')
        WINDOW = 'WINDOW', _('Window')
        AISLE = 'AISLE', _('Aisle')
    
    class SeatGender(models.TextChoices):
        ANY = 'ANY', _('Any')
        MALE = 'MALE', _('Male Only')
        FEMALE = 'FEMALE', _('Female Only')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    coach = models.ForeignKey(Coach, on_delete=models.CASCADE, related_name='seats')
    seat_number = models.CharField(_('seat number'), max_length=10)
    berth_type = models.CharField(
        _('berth type'),
        max_length=20,
        choices=BerthType.choices,
        default=BerthType.LOWER
    )
    seat_gender = models.CharField(
        _('seat gender'),
        max_length=10,
        choices=SeatGender.choices,
        default=SeatGender.ANY
    )
    
    # Position
    compartment_number = models.PositiveIntegerField(_('compartment number'))
    seat_position = models.PositiveIntegerField(_('seat position'))
    
    # Pricing
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
    is_emergency_window = models.BooleanField(_('emergency window'), default=False)
    is_near_toilet = models.BooleanField(_('near toilet'), default=False)
    is_near_door = models.BooleanField(_('near door'), default=False)
    
    class Meta:
        ordering = ['coach', 'compartment_number', 'seat_position']
        verbose_name = _('Seat')
        verbose_name_plural = _('Seats')
        unique_together = ['coach', 'seat_number']
        indexes = [
            models.Index(fields=['coach', 'is_booked', 'is_blocked']),
            models.Index(fields=['berth_type']),
        ]
    
    def __str__(self):
        return f"Seat {self.seat_number} - {self.coach}"
    
    @property
    def is_available(self):
        return not (self.is_booked or self.is_blocked)
    
    @property
    def seat_description(self):
        return f"Seat {self.seat_number} ({self.get_berth_type_display()})"


class TrainStop(models.Model):
    """Train stops at stations."""
    train = models.ForeignKey(Train, on_delete=models.CASCADE, related_name='stops')
    station_name = models.CharField(_('station name'), max_length=200)
    station_code = models.CharField(_('station code'), max_length=10)
    arrival_time = models.TimeField(_('arrival time'), null=True, blank=True)
    departure_time = models.TimeField(_('departure time'), null=True, blank=True)
    halt_minutes = models.PositiveIntegerField(_('halt minutes'), default=2)
    distance_from_source = models.PositiveIntegerField(_('distance from source (km)'))
    day_number = models.PositiveIntegerField(_('day number'), default=1)
    sequence = models.PositiveIntegerField(_('sequence'))
    
    class Meta:
        ordering = ['train', 'sequence']
        verbose_name = _('Train Stop')
        verbose_name_plural = _('Train Stops')
        unique_together = ['train', 'sequence']
    
    def __str__(self):
        return f"{self.station_name} ({self.station_code}) - {self.train.train_number}"
    
    @property
    def is_source(self):
        return self.sequence == 1
    
    @property
    def is_destination(self):
        # Get max sequence for this train
        max_seq = TrainStop.objects.filter(train=self.train).aggregate(
            models.Max('sequence')
        )['sequence__max']
        return self.sequence == max_seq


class TrainBooking(models.Model):
    """Train ticket booking."""
    
    class BookingStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        CONFIRMED = 'CONFIRMED', _('Confirmed')
        RAC = 'RAC', _('RAC (Reservation Against Cancellation)')
        WAITLIST = 'WAITLIST', _('Waitlisted')
        CANCELLED = 'CANCELLED', _('Cancelled')
        NO_SHOW = 'NO_SHOW', _('No Show')
    
    class QuotaType(models.TextChoices):
        GENERAL = 'GENERAL', _('General')
        LADIES = 'LADIES', _('Ladies')
        SENIOR_CITIZEN = 'SENIOR_CITIZEN', _('Senior Citizen')
        TATKAL = 'TATKAL', _('Tatkal')
        PREMIUM_TATKAL = 'PREMIUM_TATKAL', _('Premium Tatkal')
        FOREIGN_TOURIST = 'FOREIGN_TOURIST', _('Foreign Tourist')
        DIVYANG = 'DIVYANG', _('Divyang (Disabled)')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='train_bookings'
    )
    train = models.ForeignKey(Train, on_delete=models.PROTECT, related_name='bookings')
    
    # Journey Details
    from_station = models.ForeignKey(
        TrainStop,
        on_delete=models.PROTECT,
        related_name='from_bookings'
    )
    to_station = models.ForeignKey(
        TrainStop,
        on_delete=models.PROTECT,
        related_name='to_bookings'
    )
    travel_date = models.DateField(_('travel date'))
    
    # Coach and Seat Details
    coach_type = models.ForeignKey(CoachType, on_delete=models.PROTECT, related_name='bookings')
    seats_booked = models.JSONField(
        _('seats booked'),
        default=list,
        help_text=_('List of seat numbers booked')
    )
    total_passengers = models.PositiveIntegerField(_('total passengers'), default=1)
    
    # Quota and Status
    quota = models.CharField(
        _('quota'),
        max_length=20,
        choices=QuotaType.choices,
        default=QuotaType.GENERAL
    )
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=BookingStatus.choices,
        default=BookingStatus.PENDING
    )
    pnr_number = models.CharField(_('PNR number'), max_length=10, unique=True, blank=True)
    
    # Fare Details
    base_fare = models.DecimalField(_('base fare'), max_digits=10, decimal_places=2)
    reservation_charge = models.DecimalField(_('reservation charge'), max_digits=10, decimal_places=2)
    superfast_charge = models.DecimalField(_('superfast charge'), max_digits=10, decimal_places=2)
    service_tax = models.DecimalField(_('service tax'), max_digits=10, decimal_places=2)
    tatkal_charge = models.DecimalField(_('tatkal charge'), max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(_('total amount'), max_digits=10, decimal_places=2)
    
    # Passenger Information
    passenger_name = models.CharField(_('passenger name'), max_length=200)
    passenger_age = models.PositiveIntegerField(_('passenger age'))
    passenger_gender = models.CharField(
        _('passenger gender'),
        max_length=10,
        choices=[('MALE', 'Male'), ('FEMALE', 'Female'), ('OTHER', 'Other')]
    )
    passenger_id_type = models.CharField(
        _('ID type'),
        max_length=20,
        choices=[
            ('AADHAAR', 'Aadhaar'),
            ('PAN', 'PAN'),
            ('PASSPORT', 'Passport'),
            ('DRIVING_LICENSE', 'Driving License'),
            ('VOTER_ID', 'Voter ID'),
        ],
        default='AADHAAR'
    )
    passenger_id_number = models.CharField(_('ID number'), max_length=50)
    
    # Contact Information
    passenger_phone = models.CharField(_('passenger phone'), max_length=20)
    passenger_email = models.EmailField(_('passenger email'), blank=True)
    
    # Cancellation
    cancellation_reason = models.TextField(_('cancellation reason'), blank=True)
    cancellation_charge = models.DecimalField(
        _('cancellation charge'),
        max_digits=10,
        decimal_places=2,
        default=0.00
    )
    cancellation_time = models.DateTimeField(_('cancellation time'), null=True, blank=True)
    
    # Timestamps
    booked_at = models.DateTimeField(_('booked at'), auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-booked_at']
        verbose_name = _('Train Booking')
        verbose_name_plural = _('Train Bookings')
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['train', 'travel_date']),
            models.Index(fields=['pnr_number']),
            models.Index(fields=['booked_at']),
        ]
    
    def __str__(self):
        return f"PNR: {self.pnr_number} - {self.train.train_number}"
    
    def save(self, *args, **kwargs):
        # Generate PNR if not exists
        if not self.pnr_number:
            self.pnr_number = self.generate_pnr()
        super().save(*args, **kwargs)
    
    def generate_pnr(self):
        """Generate 10-digit PNR number."""
        import random
        import string
        
        # Generate random 10-digit alphanumeric PNR
        while True:
            pnr = ''.join(random.choices(string.digits, k=10))
            if not TrainBooking.objects.filter(pnr_number=pnr).exists():
                return pnr
    
    @property
    def journey_distance(self):
        """Calculate journey distance in km."""
        return self.to_station.distance_from_source - self.from_station.distance_from_source
    
    @property
    def journey_duration(self):
        """Calculate journey duration in hours."""
        # Calculate based on stop timings
        # Simplified calculation
        return self.journey_distance / 50  # Assuming 50 kmph average
    
    def calculate_fare(self):
        """Calculate fare based on distance, coach type, and quota."""
        distance = self.journey_distance
        coach_type = self.coach_type
        
        # Base fare
        base_fare = distance * coach_type.base_fare_per_km
        
        # Add charges
        reservation_charge = coach_type.reservation_charge
        superfast_charge = coach_type.superfast_charge if self.train.train_type == 'SUPERFAST' else Decimal('0.00')
        
        # Tatkal charge (if applicable)
        tatkal_charge = Decimal('0.00')
        if self.quota in ['TATKAL', 'PREMIUM_TATKAL']:
            # Tatkal charges are typically a percentage of base fare
            if self.quota == 'TATKAL':
                tatkal_charge = base_fare * Decimal('0.10')  # 10% for Tatkal
            else:
                tatkal_charge = base_fare * Decimal('0.30')  # 30% for Premium Tatkal
        
        # Service tax
        service_tax = (base_fare + reservation_charge + superfast_charge + tatkal_charge) * \
                     (coach_type.service_tax_percentage / 100)
        
        total_amount = base_fare + reservation_charge + superfast_charge + tatkal_charge + service_tax
        
        return {
            'base_fare': base_fare,
            'reservation_charge': reservation_charge,
            'superfast_charge': superfast_charge,
            'tatkal_charge': tatkal_charge,
            'service_tax': service_tax,
            'total_amount': total_amount,
        }


class TrainReview(models.Model):
    """Reviews for train journeys."""
    
    class Rating(models.IntegerChoices):
        ONE = 1, '★'
        TWO = 2, '★★'
        THREE = 3, '★★★'
        FOUR = 4, '★★★★'
        FIVE = 5, '★★★★★'
    
    train = models.ForeignKey(
        Train,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='train_reviews'
    )
    booking = models.ForeignKey(
        TrainBooking,
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
    food_quality = models.PositiveIntegerField(
        _('food quality'),
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
        verbose_name = _('Train Review')
        verbose_name_plural = _('Train Reviews')
        unique_together = ['train', 'user', 'booking']
        indexes = [
            models.Index(fields=['train', 'rating']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username}'s review of {self.train.train_number}"
    
    @property
    def overall_rating(self):
        """Calculate average of all aspect ratings."""
        aspects = [self.cleanliness, self.comfort, self.punctuality, 
                  self.staff_behavior, self.food_quality, self.value_for_money]
        return sum(aspects) / len(aspects)


class FareRule(models.Model):
    """Fare calculation rules for trains."""
    coach_type = models.ForeignKey(CoachType, on_delete=models.CASCADE, related_name='fare_rules')
    from_date = models.DateField(_('effective from'))
    to_date = models.DateField(_('effective to'), null=True, blank=True)
    min_distance = models.PositiveIntegerField(_('minimum distance (km)'), default=0)
    max_distance = models.PositiveIntegerField(_('maximum distance (km)'), null=True, blank=True)
    fare_per_km = models.DecimalField(_('fare per km'), max_digits=8, decimal_places=4)
    
    class Meta:
        verbose_name = _('Fare Rule')
        verbose_name_plural = _('Fare Rules')
    
    def __str__(self):
        return f"{self.coach_type.name} - {self.fare_per_km}/km"
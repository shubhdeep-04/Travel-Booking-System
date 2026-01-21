"""
Car Rental Management Models for Travel Booking System.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid

class CarCategory(models.Model):
    """Car category classification."""
    name = models.CharField(_('category name'), max_length=100, unique=True)
    description = models.TextField(_('description'), blank=True)
    icon = models.CharField(
        _('icon'),
        max_length=50,
        blank=True,
        help_text=_('Font Awesome icon class')
    )
    order = models.PositiveIntegerField(_('order'), default=0)
    
    class Meta:
        verbose_name = _('Car Category')
        verbose_name_plural = _('Car Categories')
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name


class CarBrand(models.Model):
    """Car brand/manufacturer."""
    name = models.CharField(_('brand name'), max_length=100, unique=True)
    country = models.CharField(_('country'), max_length=100, blank=True)
    logo = models.ImageField(
        _('logo'),
        upload_to='cars/brands/',
        blank=True,
        null=True
    )
    
    class Meta:
        verbose_name = _('Car Brand')
        verbose_name_plural = _('Car Brands')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Car(models.Model):
    """Car rental vehicle."""
    
    class TransmissionType(models.TextChoices):
        MANUAL = 'MANUAL', _('Manual')
        AUTOMATIC = 'AUTOMATIC', _('Automatic')
    
    class FuelType(models.TextChoices):
        PETROL = 'PETROL', _('Petrol')
        DIESEL = 'DIESEL', _('Diesel')
        ELECTRIC = 'ELECTRIC', _('Electric')
        HYBRID = 'HYBRID', _('Hybrid')
        CNG = 'CNG', _('CNG')
    
    class CarStatus(models.TextChoices):
        AVAILABLE = 'AVAILABLE', _('Available')
        BOOKED = 'BOOKED', _('Booked')
        MAINTENANCE = 'MAINTENANCE', _('Under Maintenance')
        DAMAGED = 'DAMAGED', _('Damaged')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    registration_number = models.CharField(
        _('registration number'),
        max_length=50,
        unique=True
    )
    
    # Basic Information
    brand = models.ForeignKey(
        CarBrand,
        on_delete=models.PROTECT,
        related_name='cars'
    )
    model = models.CharField(_('model'), max_length=100)
    category = models.ForeignKey(
        CarCategory,
        on_delete=models.PROTECT,
        related_name='cars'
    )
    year = models.PositiveIntegerField(_('manufacturing year'))
    color = models.CharField(_('color'), max_length=50)
    
    # Specifications
    transmission = models.CharField(
        _('transmission'),
        max_length=20,
        choices=TransmissionType.choices,
        default=TransmissionType.AUTOMATIC
    )
    fuel_type = models.CharField(
        _('fuel type'),
        max_length=20,
        choices=FuelType.choices,
        default=FuelType.PETROL
    )
    engine_capacity = models.DecimalField(
        _('engine capacity (cc)'),
        max_digits=6,
        decimal_places=1,
        null=True,
        blank=True
    )
    mileage_kmpl = models.DecimalField(
        _('mileage (kmpl)'),
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        help_text=_('Kilometers per liter')
    )
    seating_capacity = models.PositiveIntegerField(_('seating capacity'), default=5)
    baggage_capacity = models.PositiveIntegerField(
        _('baggage capacity'),
        default=2,
        help_text=_('Number of suitcases')
    )
    
    # Features
    has_ac = models.BooleanField(_('has AC'), default=True)
    has_bluetooth = models.BooleanField(_('has Bluetooth'), default=True)
    has_gps = models.BooleanField(_('has GPS'), default=False)
    has_usb = models.BooleanField(_('has USB ports'), default=True)
    has_child_seat = models.BooleanField(_('has child seat'), default=False)
    is_airbag_available = models.BooleanField(_('airbags available'), default=True)
    is_pet_allowed = models.BooleanField(_('pet allowed'), default=False)
    
    # Rental Information
    daily_rate = models.DecimalField(
        _('daily rate'),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    weekly_rate = models.DecimalField(
        _('weekly rate'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('7-day rate (optional discount)')
    )
    monthly_rate = models.DecimalField(
        _('monthly rate'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('30-day rate (optional discount)')
    )
    security_deposit = models.DecimalField(
        _('security deposit'),
        max_digits=10,
        decimal_places=2,
        default=5000.00
    )
    km_limit_per_day = models.PositiveIntegerField(
        _('km limit per day'),
        default=250,
        help_text=_('Free kilometers per day')
    )
    extra_km_charge = models.DecimalField(
        _('extra km charge'),
        max_digits=6,
        decimal_places=2,
        default=10.00,
        help_text=_('Charge per extra kilometer')
    )
    
    # Location
    pickup_location = models.CharField(_('pickup location'), max_length=255)
    city = models.CharField(_('city'), max_length=100)
    state = models.CharField(_('state'), max_length=100)
    country = models.CharField(_('country'), max_length=100)
    latitude = models.DecimalField(
        _('latitude'),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    longitude = models.DecimalField(
        _('longitude'),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    
    # Status
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=CarStatus.choices,
        default=CarStatus.AVAILABLE
    )
    is_active = models.BooleanField(_('is active'), default=True)
    featured = models.BooleanField(_('featured'), default=False)
    
    # Images
    thumbnail = models.ImageField(
        _('thumbnail'),
        upload_to='cars/thumbnails/',
        blank=True,
        null=True
    )
    
    # Additional Information
    insurance_number = models.CharField(
        _('insurance number'),
        max_length=100,
        blank=True
    )
    insurance_valid_until = models.DateField(
        _('insurance valid until'),
        null=True,
        blank=True
    )
    last_service_date = models.DateField(_('last service date'), null=True, blank=True)
    next_service_due = models.DateField(_('next service due'), null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Car')
        verbose_name_plural = _('Cars')
        indexes = [
            models.Index(fields=['city', 'status', 'is_active']),
            models.Index(fields=['category', 'daily_rate']),
            models.Index(fields=['brand', 'model']),
            models.Index(fields=['featured']),
        ]
    
    def __str__(self):
        return f"{self.brand.name} {self.model} ({self.registration_number})"
    
    @property
    def full_name(self):
        return f"{self.brand.name} {self.model} {self.year}"
    
    @property
    def weekly_discount(self):
        """Calculate weekly discount percentage."""
        if self.weekly_rate:
            weekly_total = self.daily_rate * 7
            discount = ((weekly_total - self.weekly_rate) / weekly_total) * 100
            return round(discount, 1)
        return 0
    
    @property
    def monthly_discount(self):
        """Calculate monthly discount percentage."""
        if self.monthly_rate:
            monthly_total = self.daily_rate * 30
            discount = ((monthly_total - self.monthly_rate) / monthly_total) * 100
            return round(discount, 1)
        return 0
    
    def is_available_for_dates(self, start_date, end_date):
        """
        Check if car is available for given dates.
        In production, this would check against existing bookings.
        """
        if self.status != CarStatus.AVAILABLE or not self.is_active:
            return False
        
        # For now, just check status
        # In production: Check booking conflicts
        return True


class CarImage(models.Model):
    """Additional images for car."""
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(_('image'), upload_to='cars/gallery/')
    caption = models.CharField(_('caption'), max_length=200, blank=True)
    order = models.PositiveIntegerField(_('order'), default=0)
    
    class Meta:
        ordering = ['order']
        verbose_name = _('Car Image')
        verbose_name_plural = _('Car Images')
    
    def __str__(self):
        return f"Image for {self.car}"


class CarReview(models.Model):
    """Reviews for cars."""
    
    class Rating(models.IntegerChoices):
        ONE = 1, '★'
        TWO = 2, '★★'
        THREE = 3, '★★★'
        FOUR = 4, '★★★★'
        FIVE = 5, '★★★★★'
    
    car = models.ForeignKey(
        Car,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='car_reviews'
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
    performance = models.PositiveIntegerField(
        _('performance'),
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=5
    )
    fuel_efficiency = models.PositiveIntegerField(
        _('fuel efficiency'),
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
        verbose_name = _('Car Review')
        verbose_name_plural = _('Car Reviews')
        unique_together = ['car', 'user']
        indexes = [
            models.Index(fields=['car', 'rating']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username}'s review of {self.car}"
    
    @property
    def overall_rating(self):
        """Calculate average of all aspect ratings."""
        aspects = [self.cleanliness, self.comfort, self.performance, 
                  self.fuel_efficiency, self.value_for_money]
        return sum(aspects) / len(aspects)


class CarFeature(models.Model):
    """Features available in cars."""
    name = models.CharField(_('feature name'), max_length=100, unique=True)
    icon = models.CharField(
        _('icon'),
        max_length=50,
        blank=True,
        help_text=_('Font Awesome icon class')
    )
    description = models.TextField(_('description'), blank=True)
    
    class Meta:
        verbose_name = _('Car Feature')
        verbose_name_plural = _('Car Features')
        ordering = ['name']
    
    def __str__(self):
        return self.name
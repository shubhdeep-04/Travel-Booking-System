"""
Hotel Management Models for Travel Booking System.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid

class Hotel(models.Model):
    """Hotel model with basic information."""
    
    class StarRating(models.IntegerChoices):
        ONE = 1, '★'
        TWO = 2, '★★'
        THREE = 3, '★★★'
        FOUR = 4, '★★★★'
        FIVE = 5, '★★★★★'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('hotel name'), max_length=255)
    slug = models.SlugField(_('slug'), max_length=300, unique=True)
    description = models.TextField(_('description'), blank=True)
    
    # Location
    address = models.TextField(_('address'))
    city = models.CharField(_('city'), max_length=100)
    state = models.CharField(_('state'), max_length=100)
    country = models.CharField(_('country'), max_length=100)
    postal_code = models.CharField(_('postal code'), max_length=20)
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
    
    # Ratings and Classification
    star_rating = models.IntegerField(
        _('star rating'),
        choices=StarRating.choices,
        null=True,
        blank=True
    )
    avg_rating = models.DecimalField(
        _('average rating'),
        max_digits=3,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    review_count = models.PositiveIntegerField(_('review count'), default=0)
    
    # Contact Information
    phone = models.CharField(_('phone'), max_length=20)
    email = models.EmailField(_('email'), blank=True)
    website = models.URLField(_('website'), blank=True)
    
    # Amenities
    has_wifi = models.BooleanField(_('has WiFi'), default=False)
    has_pool = models.BooleanField(_('has pool'), default=False)
    has_gym = models.BooleanField(_('has gym'), default=False)
    has_spa = models.BooleanField(_('has spa'), default=False)
    has_restaurant = models.BooleanField(_('has restaurant'), default=False)
    has_parking = models.BooleanField(_('has parking'), default=False)
    has_airport_shuttle = models.BooleanField(_('has airport shuttle'), default=False)
    is_pet_friendly = models.BooleanField(_('pet friendly'), default=False)
    
    # Images
    thumbnail = models.ImageField(
        _('thumbnail'),
        upload_to='hotels/thumbnails/',
        blank=True,
        null=True
    )
    
    # Status
    is_active = models.BooleanField(_('is active'), default=True)
    featured = models.BooleanField(_('featured'), default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Hotel')
        verbose_name_plural = _('Hotels')
        indexes = [
            models.Index(fields=['city', 'is_active']),
            models.Index(fields=['avg_rating']),
            models.Index(fields=['star_rating']),
            models.Index(fields=['featured']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.city}, {self.country}"
    
    @property
    def full_address(self):
        return f"{self.address}, {self.city}, {self.state}, {self.country} - {self.postal_code}"
    
    @property
    def available_rooms(self):
        """Count of all available rooms across all room types."""
        return self.rooms.filter(is_available=True, hotelroom__available_rooms__gt=0).count()
    
    def update_rating(self, new_rating):
        """Update average rating when new review is added."""
        total_rating = self.avg_rating * self.review_count
        self.review_count += 1
        self.avg_rating = (total_rating + new_rating) / self.review_count
        self.save(update_fields=['avg_rating', 'review_count'])


class HotelImage(models.Model):
    """Additional images for hotel."""
    hotel = models.ForeignKey(
        Hotel, 
        on_delete=models.CASCADE, 
        related_name='images'
    )
    image = models.ImageField(
        _('image'),
        upload_to='hotels/gallery/'
    )
    caption = models.CharField(_('caption'), max_length=200, blank=True)
    order = models.PositiveIntegerField(_('order'), default=0)
    
    class Meta:
        ordering = ['order']
        verbose_name = _('Hotel Image')
        verbose_name_plural = _('Hotel Images')
    
    def __str__(self):
        return f"Image for {self.hotel.name}"


class RoomType(models.Model):
    """Room type classification (Standard, Deluxe, Suite, etc.)."""
    name = models.CharField(_('room type'), max_length=100, unique=True)
    description = models.TextField(_('description'), blank=True)
    icon_class = models.CharField(
        _('icon class'),
        max_length=50,
        blank=True,
        help_text=_('CSS class for icon (e.g., "fas fa-bed")')
    )
    
    class Meta:
        verbose_name = _('Room Type')
        verbose_name_plural = _('Room Types')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class HotelRoom(models.Model):
    """Hotel room inventory and pricing."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.CASCADE,
        related_name='rooms'
    )
    room_type = models.ForeignKey(
        RoomType,
        on_delete=models.PROTECT,
        related_name='hotel_rooms'
    )
    room_number = models.CharField(_('room number'), max_length=20, blank=True)
    
    # Room Details
    name = models.CharField(_('room name'), max_length=200)
    description = models.TextField(_('description'), blank=True)
    size_sqft = models.PositiveIntegerField(
        _('room size (sq ft)'),
        null=True,
        blank=True
    )
    max_guests = models.PositiveIntegerField(_('maximum guests'), default=2)
    
    # Bed Configuration
    bed_count = models.PositiveIntegerField(_('number of beds'), default=1)
    bed_type = models.CharField(
        _('bed type'),
        max_length=50,
        default='Double',
        choices=[
            ('Single', 'Single'),
            ('Double', 'Double'),
            ('Queen', 'Queen'),
            ('King', 'King'),
            ('Twin', 'Twin'),
        ]
    )
    
    # Amenities
    has_ac = models.BooleanField(_('has AC'), default=True)
    has_tv = models.BooleanField(_('has TV'), default=True)
    has_minibar = models.BooleanField(_('has minibar'), default=False)
    has_safe = models.BooleanField(_('has safe'), default=False)
    has_balcony = models.BooleanField(_('has balcony'), default=False)
    has_bathtub = models.BooleanField(_('has bathtub'), default=False)
    is_smoking_allowed = models.BooleanField(_('smoking allowed'), default=False)
    
    # Inventory and Pricing
    total_rooms = models.PositiveIntegerField(_('total rooms'), default=1)
    available_rooms = models.PositiveIntegerField(_('available rooms'), default=1)
    base_price = models.DecimalField(
        _('base price per night'),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    tax_percentage = models.DecimalField(
        _('tax percentage'),
        max_digits=5,
        decimal_places=2,
        default=10.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # Cancellation Policy
    cancellation_days = models.PositiveIntegerField(
        _('free cancellation days'),
        default=2,
        help_text=_('Days before check-in for free cancellation')
    )
    cancellation_fee_percentage = models.DecimalField(
        _('cancellation fee percentage'),
        max_digits=5,
        decimal_places=2,
        default=10.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # Status
    is_available = models.BooleanField(_('is available'), default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['hotel', 'room_type', 'base_price']
        verbose_name = _('Hotel Room')
        verbose_name_plural = _('Hotel Rooms')
        unique_together = ['hotel', 'room_number']
        indexes = [
            models.Index(fields=['hotel', 'is_available']),
            models.Index(fields=['base_price']),
        ]
    
    def __str__(self):
        return f"{self.hotel.name} - {self.name} ({self.room_type})"
    
    @property
    def final_price(self):
        """Calculate price including tax."""
        tax_amount = (self.base_price * self.tax_percentage) / 100
        return self.base_price + tax_amount
    
    @property
    def is_sold_out(self):
        """Check if room is sold out."""
        return self.available_rooms == 0
    
    def check_availability(self, check_in, check_out, rooms_needed=1):
        """
        Check room availability for given dates.
        This is a simplified version - in production, you'd check against bookings.
        """
        if not self.is_available:
            return False
        if self.available_rooms < rooms_needed:
            return False
        return True
    
    def reserve_rooms(self, count=1):
        """Reserve rooms from inventory."""
        if self.available_rooms >= count:
            self.available_rooms -= count
            self.save(update_fields=['available_rooms'])
            return True
        return False
    
    def release_rooms(self, count=1):
        """Release rooms back to inventory."""
        self.available_rooms += count
        if self.available_rooms > self.total_rooms:
            self.available_rooms = self.total_rooms
        self.save(update_fields=['available_rooms'])
    
    def get_cancellation_fee(self, booking_amount):
        """Calculate cancellation fee."""
        return (booking_amount * self.cancellation_fee_percentage) / 100


class RoomImage(models.Model):
    """Images for specific rooms."""
    room = models.ForeignKey(
        HotelRoom,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(
        _('image'),
        upload_to='hotels/rooms/'
    )
    caption = models.CharField(_('caption'), max_length=200, blank=True)
    is_primary = models.BooleanField(_('primary image'), default=False)
    order = models.PositiveIntegerField(_('order'), default=0)
    
    class Meta:
        ordering = ['-is_primary', 'order']
        verbose_name = _('Room Image')
        verbose_name_plural = _('Room Images')
    
    def __str__(self):
        return f"Image for {self.room.name}"
    
    def save(self, *args, **kwargs):
        # Ensure only one primary image per room
        if self.is_primary:
            RoomImage.objects.filter(room=self.room, is_primary=True).update(is_primary=False)
        super().save(*args, **kwargs)


class HotelReview(models.Model):
    """Reviews and ratings for hotels."""
    
    class Rating(models.IntegerChoices):
        ONE = 1, '★'
        TWO = 2, '★★'
        THREE = 3, '★★★'
        FOUR = 4, '★★★★'
        FIVE = 5, '★★★★★'
    
    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='hotel_reviews'
    )
    rating = models.IntegerField(_('rating'), choices=Rating.choices)
    title = models.CharField(_('review title'), max_length=200)
    comment = models.TextField(_('comment'))
    
    # Review aspects (1-5)
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
    location = models.PositiveIntegerField(
        _('location'),
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=5
    )
    facilities = models.PositiveIntegerField(
        _('facilities'),
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=5
    )
    staff = models.PositiveIntegerField(
        _('staff'),
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
        verbose_name = _('Hotel Review')
        verbose_name_plural = _('Hotel Reviews')
        unique_together = ['hotel', 'user']
        indexes = [
            models.Index(fields=['hotel', 'rating']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username}'s review of {self.hotel.name}"
    
    @property
    def overall_rating(self):
        """Calculate average of all aspect ratings."""
        aspects = [self.cleanliness, self.comfort, self.location, 
                  self.facilities, self.staff, self.value_for_money]
        return sum(aspects) / len(aspects)
    
    def save(self, *args, **kwargs):
        """Update hotel rating when review is saved."""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            self.hotel.update_rating(self.rating)


class HotelAmenity(models.Model):
    """Amenity tags for hotels."""
    name = models.CharField(_('amenity name'), max_length=100, unique=True)
    icon = models.CharField(
        _('icon'),
        max_length=50,
        blank=True,
        help_text=_('Font Awesome icon class')
    )
    description = models.TextField(_('description'), blank=True)
    
    class Meta:
        verbose_name = _('Hotel Amenity')
        verbose_name_plural = _('Hotel Amenities')
        ordering = ['name']
    
    def __str__(self):
        return self.name
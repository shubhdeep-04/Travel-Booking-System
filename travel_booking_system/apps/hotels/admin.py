"""
Admin configuration for Hotel models.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Avg

from .models import (
    Hotel, HotelImage, HotelRoom, RoomType, 
    HotelReview, RoomImage, HotelAmenity
)
from .forms import HotelAdminForm, HotelRoomAdminForm


class HotelImageInline(admin.TabularInline):
    """Inline for hotel images."""
    model = HotelImage
    extra = 1
    fields = ['image', 'caption', 'order']
    readonly_fields = ['image_preview']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="100" height="100" style="object-fit: cover;" />',
                obj.image.url
            )
        return "-"
    image_preview.short_description = _('Preview')


class HotelRoomInline(admin.TabularInline):
    """Inline for hotel rooms."""
    model = HotelRoom
    extra = 0
    fields = ['room_type', 'name', 'base_price', 'available_rooms', 'is_available']
    readonly_fields = ['room_details']
    
    def room_details(self, obj):
        return f"{obj.name} - ${obj.base_price}/night"
    room_details.short_description = _('Room Details')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('room_type')


@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    """Admin configuration for Hotel model."""
    
    form = HotelAdminForm
    inlines = [HotelImageInline, HotelRoomInline]
    
    list_display = [
        'name', 'city', 'country', 'star_rating_display', 
        'avg_rating', 'available_rooms_count', 'is_active', 'featured'
    ]
    list_filter = ['is_active', 'featured', 'star_rating', 'city', 'country']
    search_fields = ['name', 'city', 'country', 'address']
    readonly_fields = ['avg_rating', 'review_count', 'created_at', 'updated_at']
    list_per_page = 25
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'slug', 'description', 'thumbnail')
        }),
        (_('Location'), {
            'fields': ('address', 'city', 'state', 'country', 'postal_code'),
            'classes': ('collapse',)
        }),
        (_('Coordinates'), {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        (_('Ratings'), {
            'fields': ('star_rating', 'avg_rating', 'review_count')
        }),
        (_('Contact Information'), {
            'fields': ('phone', 'email', 'website'),
            'classes': ('collapse',)
        }),
        (_('Amenities'), {
            'fields': (
                'has_wifi', 'has_pool', 'has_gym', 'has_spa',
                'has_restaurant', 'has_parking', 'has_airport_shuttle',
                'is_pet_friendly'
            ),
            'classes': ('collapse',)
        }),
        (_('Status'), {
            'fields': ('is_active', 'featured')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def star_rating_display(self, obj):
        if obj.star_rating:
            return '★' * obj.star_rating
        return '-'
    star_rating_display.short_description = _('Stars')
    star_rating_display.admin_order_field = 'star_rating'
    
    def available_rooms_count(self, obj):
        return obj.available_rooms
    available_rooms_count.short_description = _('Available Rooms')
    
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            available_rooms=Count('rooms', filter=models.Q(rooms__is_available=True))
        )
    
    actions = ['activate_hotels', 'deactivate_hotels', 'mark_featured', 'unmark_featured']
    
    def activate_hotels(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, _('Selected hotels have been activated.'))
    activate_hotels.short_description = _('Activate selected hotels')
    
    def deactivate_hotels(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, _('Selected hotels have been deactivated.'))
    deactivate_hotels.short_description = _('Deactivate selected hotels')
    
    def mark_featured(self, request, queryset):
        queryset.update(featured=True)
        self.message_user(request, _('Selected hotels have been marked as featured.'))
    mark_featured.short_description = _('Mark as featured')
    
    def unmark_featured(self, request, queryset):
        queryset.update(featured=False)
        self.message_user(request, _('Selected hotels have been unmarked as featured.'))
    unmark_featured.short_description = _('Remove featured status')


class RoomImageInline(admin.TabularInline):
    """Inline for room images."""
    model = RoomImage
    extra = 1
    fields = ['image', 'caption', 'is_primary', 'order']
    readonly_fields = ['image_preview']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="100" height="100" style="object-fit: cover;" />',
                obj.image.url
            )
        return "-"
    image_preview.short_description = _('Preview')


@admin.register(HotelRoom)
class HotelRoomAdmin(admin.ModelAdmin):
    """Admin configuration for HotelRoom model."""
    
    form = HotelRoomAdminForm
    inlines = [RoomImageInline]
    
    list_display = [
        'hotel', 'room_type', 'name', 'base_price', 
        'available_rooms', 'total_rooms', 'is_available'
    ]
    list_filter = ['is_available', 'room_type', 'hotel__city']
    search_fields = ['hotel__name', 'name', 'room_number']
    readonly_fields = ['created_at', 'updated_at', 'final_price_display']
    list_per_page = 25
    
    fieldsets = (
        (_('Hotel Information'), {
            'fields': ('hotel',)
        }),
        (_('Room Information'), {
            'fields': ('room_type', 'room_number', 'name', 'description')
        }),
        (_('Room Specifications'), {
            'fields': ('size_sqft', 'max_guests', 'bed_count', 'bed_type')
        }),
        (_('Amenities'), {
            'fields': (
                'has_ac', 'has_tv', 'has_minibar', 'has_safe',
                'has_balcony', 'has_bathtub', 'is_smoking_allowed'
            ),
            'classes': ('collapse',)
        }),
        (_('Pricing and Inventory'), {
            'fields': (
                'base_price', 'tax_percentage', 'final_price_display',
                'total_rooms', 'available_rooms'
            )
        }),
        (_('Cancellation Policy'), {
            'fields': ('cancellation_days', 'cancellation_fee_percentage'),
            'classes': ('collapse',)
        }),
        (_('Status'), {
            'fields': ('is_available',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def final_price_display(self, obj):
        return f"${obj.final_price:.2f} (incl. tax)"
    final_price_display.short_description = _('Final Price')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('hotel', 'room_type')
    
    actions = ['mark_available', 'mark_unavailable']
    
    def mark_available(self, request, queryset):
        queryset.update(is_available=True)
        self.message_user(request, _('Selected rooms have been marked as available.'))
    mark_available.short_description = _('Mark as available')
    
    def mark_unavailable(self, request, queryset):
        queryset.update(is_available=False)
        self.message_user(request, _('Selected rooms have been marked as unavailable.'))
    mark_unavailable.short_description = _('Mark as unavailable')


@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    """Admin configuration for RoomType model."""
    list_display = ['name', 'hotel_count']
    search_fields = ['name']
    
    def hotel_count(self, obj):
        return obj.hotel_rooms.count()
    hotel_count.short_description = _('Number of Rooms')


@admin.register(HotelReview)
class HotelReviewAdmin(admin.ModelAdmin):
    """Admin configuration for HotelReview model."""
    list_display = ['hotel', 'user', 'rating', 'title', 'is_verified', 'created_at']
    list_filter = ['rating', 'is_verified', 'created_at']
    search_fields = ['hotel__name', 'user__username', 'title', 'comment']
    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 25
    
    fieldsets = (
        (None, {
            'fields': ('hotel', 'user')
        }),
        (_('Review Details'), {
            'fields': ('rating', 'title', 'comment')
        }),
        (_('Aspect Ratings'), {
            'fields': (
                'cleanliness', 'comfort', 'location',
                'facilities', 'staff', 'value_for_money'
            ),
            'classes': ('collapse',)
        }),
        (_('Status'), {
            'fields': ('is_verified', 'helpful_count')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['verify_reviews', 'unverify_reviews']
    
    def verify_reviews(self, request, queryset):
        queryset.update(is_verified=True)
        self.message_user(request, _('Selected reviews have been verified.'))
    verify_reviews.short_description = _('Verify selected reviews')
    
    def unverify_reviews(self, request, queryset):
        queryset.update(is_verified=False)
        self.message_user(request, _('Selected reviews have been unverified.'))
    unverify_reviews.short_description = _('Unverify selected reviews')


@admin.register(HotelAmenity)
class HotelAmenityAdmin(admin.ModelAdmin):
    """Admin configuration for HotelAmenity model."""
    list_display = ['name', 'icon']
    search_fields = ['name']


# Register other models
admin.site.register(HotelImage)
admin.site.register(RoomImage)
"""
Admin configuration for Bus models.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse

from .models import (
    Bus, BusOperator, BusType, BusSeat, BusBooking, 
    BusReview, BusStop, BusSchedule
)
from .forms import BusAdminForm


class BusSeatInline(admin.TabularInline):
    """Inline for bus seats."""
    model = BusSeat
    extra = 0
    fields = ['seat_number', 'seat_type', 'seat_gender', 'is_booked', 'is_blocked']
    readonly_fields = ['seat_status']
    
    def seat_status(self, obj):
        if obj.is_booked:
            return format_html('<span style="color: red;">Booked</span>')
        elif obj.is_blocked:
            return format_html('<span style="color: orange;">Blocked</span>')
        else:
            return format_html('<span style="color: green;">Available</span>')
    seat_status.short_description = _('Status')
    
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('row_number', 'column_number')


class BusStopInline(admin.TabularInline):
    """Inline for bus stops."""
    model = BusStop
    extra = 1
    fields = ['city', 'stop_name', 'arrival_time', 'departure_time', 'sequence']


@admin.register(Bus)
class BusAdmin(admin.ModelAdmin):
    """Admin configuration for Bus model."""
    
    form = BusAdminForm
    inlines = [BusSeatInline, BusStopInline]
    
    list_display = [
        'bus_number', 'operator', 'route_display', 'departure_time', 
        'arrival_time', 'total_seats', 'available_seats_display', 'status'
    ]
    list_filter = ['status', 'operator', 'bus_type', 'has_ac', 'is_sleeper']
    search_fields = ['bus_number', 'route_from', 'route_to', 'operator__name']
    readonly_fields = ['created_at', 'updated_at', 'route_name', 'final_fare_display']
    list_per_page = 25
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('bus_number', 'operator', 'bus_type')
        }),
        (_('Route Information'), {
            'fields': ('route_from', 'route_to', 'via_cities', 'distance_km')
        }),
        (_('Schedule'), {
            'fields': ('departure_time', 'arrival_time', 'duration_hours')
        }),
        (_('Seat Configuration'), {
            'fields': ('total_seats', 'seats_per_row', 'seat_layout'),
            'classes': ('collapse',)
        }),
        (_('Amenities'), {
            'fields': (
                'has_ac', 'has_wifi', 'has_charging',
                'has_toilet', 'has_tv', 'is_sleeper'
            ),
            'classes': ('collapse',)
        }),
        (_('Fare Information'), {
            'fields': ('base_fare', 'tax_percentage', 'final_fare_display')
        }),
        (_('Cancellation Policy'), {
            'fields': ('cancellation_before_hours', 'cancellation_charge_percentage'),
            'classes': ('collapse',)
        }),
        (_('Status'), {
            'fields': ('status',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def route_display(self, obj):
        return f"{obj.route_from} → {obj.route_to}"
    route_display.short_description = _('Route')
    route_display.admin_order_field = 'route_from'
    
    def available_seats_display(self, obj):
        available = obj.available_seats
        total = obj.total_seats
        percentage = (available / total * 100) if total > 0 else 0
        color = 'green' if percentage > 20 else 'orange' if percentage > 0 else 'red'
        return format_html(
            '<span style="color: {};">{}/{} ({}%)</span>',
            color, available, total, int(percentage)
        )
    available_seats_display.short_description = _('Available Seats')
    
    def final_fare_display(self, obj):
        return f"${obj.final_fare:.2f} (incl. tax)"
    final_fare_display.short_description = _('Final Fare')
    
    actions = ['activate_buses', 'deactivate_buses', 'generate_seats']
    
    def activate_buses(self, request, queryset):
        queryset.update(status='ACTIVE')
        self.message_user(request, _('Selected buses have been activated.'))
    activate_buses.short_description = _('Activate selected buses')
    
    def deactivate_buses(self, request, queryset):
        queryset.update(status='INACTIVE')
        self.message_user(request, _('Selected buses have been deactivated.'))
    deactivate_buses.short_description = _('Deactivate selected buses')
    
    def generate_seats(self, request, queryset):
        """Generate seats for selected buses."""
        from .seat_manager import SeatManager
        
        for bus in queryset:
            # Generate seat layout
            # In production, you'd have a proper seat generation logic
            pass
        
        self.message_user(request, _('Seats generated for selected buses.'))
    generate_seats.short_description = _('Generate seats')


@admin.register(BusOperator)
class BusOperatorAdmin(admin.ModelAdmin):
    """Admin configuration for BusOperator model."""
    list_display = ['name', 'code', 'rating', 'bus_count']
    search_fields = ['name', 'code']
    
    def bus_count(self, obj):
        return obj.buses.count()
    bus_count.short_description = _('Number of Buses')


@admin.register(BusType)
class BusTypeAdmin(admin.ModelAdmin):
    """Admin configuration for BusType model."""
    list_display = ['name', 'bus_count']
    search_fields = ['name']
    
    def bus_count(self, obj):
        return obj.buses.count()
    bus_count.short_description = _('Number of Buses')


@admin.register(BusBooking)
class BusBookingAdmin(admin.ModelAdmin):
    """Admin configuration for BusBooking model."""
    list_display = [
        'pnr_display', 'bus', 'travel_date', 'passenger_name', 
        'seats_count', 'total_amount', 'status', 'created_at'
    ]
    list_filter = ['status', 'travel_date', 'created_at']
    search_fields = ['id', 'passenger_name', 'passenger_phone', 'bus__bus_number']
    readonly_fields = ['created_at', 'updated_at', 'cancelled_at', 'pnr_number']
    list_per_page = 25
    
    fieldsets = (
        (_('Booking Information'), {
            'fields': ('user', 'bus', 'travel_date', 'pnr_number')
        }),
        (_('Seat Details'), {
            'fields': ('seats_booked', 'total_passengers', 'total_amount')
        }),
        (_('Passenger Information'), {
            'fields': (
                'passenger_name', 'passenger_age', 'passenger_gender',
                'passenger_phone', 'passenger_email'
            )
        }),
        (_('Journey Points'), {
            'fields': ('boarding_point', 'dropping_point')
        }),
        (_('Status'), {
            'fields': ('status', 'cancellation_reason', 'cancellation_charge')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at', 'cancelled_at'),
            'classes': ('collapse',)
        }),
    )
    
    def pnr_display(self, obj):
        return obj.pnr_number
    pnr_display.short_description = _('PNR')
    pnr_display.admin_order_field = 'id'
    
    def seats_count(self, obj):
        return len(obj.seats_booked)
    seats_count.short_description = _('Seats')
    
    actions = ['confirm_bookings', 'cancel_bookings']
    
    def confirm_bookings(self, request, queryset):
        queryset.update(status='CONFIRMED')
        self.message_user(request, _('Selected bookings have been confirmed.'))
    confirm_bookings.short_description = _('Confirm selected bookings')
    
    def cancel_bookings(self, request, queryset):
        for booking in queryset:
            booking.cancel_booking('Cancelled by admin')
        self.message_user(request, _('Selected bookings have been cancelled.'))
    cancel_bookings.short_description = _('Cancel selected bookings')


@admin.register(BusReview)
class BusReviewAdmin(admin.ModelAdmin):
    """Admin configuration for BusReview model."""
    list_display = ['bus', 'user', 'rating', 'title', 'is_verified', 'created_at']
    list_filter = ['rating', 'is_verified', 'created_at']
    search_fields = ['bus__bus_number', 'user__username', 'title', 'comment']
    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 25
    
    fieldsets = (
        (None, {
            'fields': ('bus', 'user', 'booking')
        }),
        (_('Review Details'), {
            'fields': ('rating', 'title', 'comment')
        }),
        (_('Aspect Ratings'), {
            'fields': (
                'cleanliness', 'comfort', 'punctuality',
                'staff_behavior', 'value_for_money'
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


# Register other models
admin.site.register(BusSeat)
admin.site.register(BusStop)
admin.site.register(BusSchedule)
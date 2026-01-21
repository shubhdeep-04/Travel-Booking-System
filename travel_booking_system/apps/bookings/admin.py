"""
Admin configuration for Booking models.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse

from .models import Booking, BookingHistory, BookingDocument
from .forms import BookingAdminForm


class BookingHistoryInline(admin.TabularInline):
    """Inline for booking history."""
    model = BookingHistory
    extra = 0
    readonly_fields = ['old_status', 'new_status', 'changed_by', 'notes', 'created_at']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


class BookingDocumentInline(admin.TabularInline):
    """Inline for booking documents."""
    model = BookingDocument
    extra = 0
    fields = ['document_type', 'name', 'file', 'is_verified']
    readonly_fields = ['file_preview']
    
    def file_preview(self, obj):
        if obj.file:
            return format_html(
                '<a href="{}" target="_blank">View</a>',
                obj.file.url
            )
        return "-"
    file_preview.short_description = _('Preview')


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    """Admin configuration for Booking model."""
    
    form = BookingAdminForm
    inlines = [BookingHistoryInline, BookingDocumentInline]
    
    list_display = [
        'booking_reference', 'user', 'service_type_display', 
        'service_name_display', 'booking_date', 'total_amount_display',
        'status_display', 'is_upcoming'
    ]
    list_filter = ['status', 'service_type', 'booking_date', 'created_at']
    search_fields = ['booking_reference', 'user__username', 'user__email', 
                    'contact_name', 'contact_email', 'contact_phone']
    readonly_fields = ['booking_reference', 'created_at', 'updated_at', 
                      'cancellation_date', 'refund_amount']
    list_per_page = 50
    actions = ['confirm_selected', 'cancel_selected', 'mark_completed']
    
    fieldsets = (
        (_('Booking Information'), {
            'fields': ('booking_reference', 'user', 'booking_date')
        }),
        (_('Service Details'), {
            'fields': ('service_type', 'service_id', 'metadata')
        }),
        (_('Dates'), {
            'fields': ('check_in_date', 'check_out_date', 'travel_date')
        }),
        (_('Passenger/Occupant Details'), {
            'fields': ('quantity', 'adults', 'children')
        }),
        (_('Pricing'), {
            'fields': ('base_amount', 'tax_amount', 'discount_amount', 'total_amount')
        }),
        (_('Status'), {
            'fields': ('status',)
        }),
        (_('Contact Information'), {
            'fields': ('contact_name', 'contact_email', 'contact_phone')
        }),
        (_('Special Requests'), {
            'fields': ('special_requests',),
            'classes': ('collapse',)
        }),
        (_('Cancellation Details'), {
            'fields': ('cancellation_reason', 'cancellation_date', 'refund_amount'),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def service_type_display(self, obj):
        return obj.get_service_type_display()
    service_type_display.short_description = _('Service Type')
    service_type_display.admin_order_field = 'service_type'
    
    def service_name_display(self, obj):
        return obj.service_name
    service_name_display.short_description = _('Service Name')
    
    def total_amount_display(self, obj):
        return f"${obj.total_amount:.2f}"
    total_amount_display.short_description = _('Amount')
    total_amount_display.admin_order_field = 'total_amount'
    
    def status_display(self, obj):
        status_colors = {
            'PENDING': 'warning',
            'CONFIRMED': 'success',
            'CANCELLED': 'danger',
            'COMPLETED': 'info',
            'FAILED': 'secondary',
            'REFUNDED': 'primary',
        }
        color = status_colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge badge-{}">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = _('Status')
    
    def is_upcoming(self, obj):
        return obj.is_upcoming
    is_upcoming.short_description = _('Upcoming')
    is_upcoming.boolean = True
    
    def confirm_selected(self, request, queryset):
        from .utils import BookingManager
        
        count = 0
        for booking in queryset:
            success, message = BookingManager.confirm_booking(str(booking.id))
            if success:
                count += 1
        
        self.message_user(request, _(f'{count} booking(s) confirmed.'))
    confirm_selected.short_description = _('Confirm selected bookings')
    
    def cancel_selected(self, request, queryset):
        count = 0
        for booking in queryset:
            if booking.status in ['PENDING', 'CONFIRMED']:
                booking.cancel("Cancelled by admin")
                count += 1
        
        self.message_user(request, _(f'{count} booking(s) cancelled.'))
    cancel_selected.short_description = _('Cancel selected bookings')
    
    def mark_completed(self, request, queryset):
        queryset.update(status='COMPLETED')
        self.message_user(request, _(f'{len(queryset)} booking(s) marked as completed.'))
    mark_completed.short_description = _('Mark as completed')


@admin.register(BookingHistory)
class BookingHistoryAdmin(admin.ModelAdmin):
    """Admin configuration for BookingHistory model."""
    list_display = ['booking', 'old_status', 'new_status', 'changed_by', 'created_at']
    list_filter = ['created_at', 'new_status']
    search_fields = ['booking__booking_reference', 'changed_by__username', 'notes']
    readonly_fields = ['booking', 'old_status', 'new_status', 'changed_by', 
                      'notes', 'metadata', 'created_at']
    list_per_page = 100
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(BookingDocument)
class BookingDocumentAdmin(admin.ModelAdmin):
    """Admin configuration for BookingDocument model."""
    list_display = ['booking', 'document_type', 'name', 'is_verified', 'created_at']
    list_filter = ['document_type', 'is_verified', 'created_at']
    search_fields = ['booking__booking_reference', 'name', 'description']
    readonly_fields = ['created_at', 'file_preview']
    list_per_page = 50
    
    fieldsets = (
        (None, {
            'fields': ('booking', 'document_type')
        }),
        (_('Document Details'), {
            'fields': ('name', 'description', 'file', 'file_preview')
        }),
        (_('Status'), {
            'fields': ('is_verified', 'uploaded_by')
        }),
        (_('Timestamps'), {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def file_preview(self, obj):
        if obj.file:
            return format_html(
                '<a href="{}" target="_blank">Download</a>',
                obj.file.url
            )
        return "-"
    file_preview.short_description = _('File')
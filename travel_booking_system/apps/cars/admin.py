"""
Admin configuration for Car models.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse

from .models import Car, CarCategory, CarBrand, CarImage, CarReview, CarFeature
from .forms import CarAdminForm


class CarImageInline(admin.TabularInline):
    """Inline for car images."""
    model = CarImage
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


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    """Admin configuration for Car model."""
    
    form = CarAdminForm
    inlines = [CarImageInline]
    
    list_display = [
        'registration_number', 'brand_model_display', 'category', 
        'city', 'daily_rate', 'status', 'is_active'
    ]
    list_filter = ['status', 'is_active', 'category', 'brand', 'city', 'fuel_type']
    search_fields = ['registration_number', 'brand__name', 'model', 'city']
    readonly_fields = ['created_at', 'updated_at', 'weekly_discount_display', 
                      'monthly_discount_display']
    list_per_page = 25
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('registration_number', 'brand', 'model', 'category', 
                      'year', 'color', 'thumbnail')
        }),
        (_('Specifications'), {
            'fields': ('transmission', 'fuel_type', 'engine_capacity', 
                      'mileage_kmpl', 'seating_capacity', 'baggage_capacity')
        }),
        (_('Features'), {
            'fields': (
                'has_ac', 'has_bluetooth', 'has_gps', 'has_usb',
                'has_child_seat', 'is_airbag_available', 'is_pet_allowed'
            ),
            'classes': ('collapse',)
        }),
        (_('Rental Information'), {
            'fields': (
                'daily_rate', 'weekly_rate', 'weekly_discount_display',
                'monthly_rate', 'monthly_discount_display',
                'security_deposit', 'km_limit_per_day', 'extra_km_charge'
            )
        }),
        (_('Location'), {
            'fields': ('pickup_location', 'city', 'state', 'country',
                      'latitude', 'longitude')
        }),
        (_('Status'), {
            'fields': ('status', 'is_active', 'featured')
        }),
        (_('Insurance & Maintenance'), {
            'fields': ('insurance_number', 'insurance_valid_until',
                      'last_service_date', 'next_service_due'),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def brand_model_display(self, obj):
        return f"{obj.brand.name} {obj.model}"
    brand_model_display.short_description = _('Car')
    brand_model_display.admin_order_field = 'brand__name'
    
    def weekly_discount_display(self, obj):
        discount = obj.weekly_discount
        if discount > 0:
            return f"{discount}% discount"
        return "-"
    weekly_discount_display.short_description = _('Weekly Discount')
    
    def monthly_discount_display(self, obj):
        discount = obj.monthly_discount
        if discount > 0:
            return f"{discount}% discount"
        return "-"
    monthly_discount_display.short_description = _('Monthly Discount')
    
    actions = ['mark_available', 'mark_maintenance', 'activate_cars', 'deactivate_cars']
    
    def mark_available(self, request, queryset):
        queryset.update(status='AVAILABLE')
        self.message_user(request, _('Selected cars have been marked as available.'))
    mark_available.short_description = _('Mark as available')
    
    def mark_maintenance(self, request, queryset):
        queryset.update(status='MAINTENANCE')
        self.message_user(request, _('Selected cars have been marked as under maintenance.'))
    mark_maintenance.short_description = _('Mark as under maintenance')
    
    def activate_cars(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, _('Selected cars have been activated.'))
    activate_cars.short_description = _('Activate selected cars')
    
    def deactivate_cars(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, _('Selected cars have been deactivated.'))
    deactivate_cars.short_description = _('Deactivate selected cars')


@admin.register(CarBrand)
class CarBrandAdmin(admin.ModelAdmin):
    """Admin configuration for CarBrand model."""
    list_display = ['name', 'country', 'car_count']
    search_fields = ['name', 'country']
    
    def car_count(self, obj):
        return obj.cars.count()
    car_count.short_description = _('Number of Cars')


@admin.register(CarCategory)
class CarCategoryAdmin(admin.ModelAdmin):
    """Admin configuration for CarCategory model."""
    list_display = ['name', 'order', 'car_count']
    search_fields = ['name']
    list_editable = ['order']
    
    def car_count(self, obj):
        return obj.cars.count()
    car_count.short_description = _('Number of Cars')


@admin.register(CarReview)
class CarReviewAdmin(admin.ModelAdmin):
    """Admin configuration for CarReview model."""
    list_display = ['car', 'user', 'rating', 'title', 'is_verified', 'created_at']
    list_filter = ['rating', 'is_verified', 'created_at']
    search_fields = ['car__registration_number', 'user__username', 'title', 'comment']
    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 25
    
    fieldsets = (
        (None, {
            'fields': ('car', 'user')
        }),
        (_('Review Details'), {
            'fields': ('rating', 'title', 'comment')
        }),
        (_('Aspect Ratings'), {
            'fields': (
                'cleanliness', 'comfort', 'performance',
                'fuel_efficiency', 'value_for_money'
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


@admin.register(CarFeature)
class CarFeatureAdmin(admin.ModelAdmin):
    """Admin configuration for CarFeature model."""
    list_display = ['name', 'icon']
    search_fields = ['name']


# Register other models
admin.site.register(CarImage)
"""
Unified Booking Management Models for Travel Booking System.
All bookings (Hotel, Car, Bus, Train) are stored here.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from decimal import Decimal
import uuid
import json


class Booking(models.Model):
    """
    Unified booking model for all services (Hotel, Car, Bus, Train).
    Uses generic foreign key to link to any service.
    """
    
    class ServiceType(models.TextChoices):
        HOTEL = 'HOTEL', _('Hotel')
        CAR = 'CAR', _('Car Rental')
        BUS = 'BUS', _('Bus Ticket')
        TRAIN = 'TRAIN', _('Train Ticket')
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        CONFIRMED = 'CONFIRMED', _('Confirmed')
        CANCELLED = 'CANCELLED', _('Cancelled')
        COMPLETED = 'COMPLETED', _('Completed')
        FAILED = 'FAILED', _('Failed')
        REFUNDED = 'REFUNDED', _('Refunded')
        WAITLISTED = 'WAITLISTED', _('Waitlisted')
        RAC = 'RAC', _('RAC (Reservation Against Cancellation)')
    
    class PaymentStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        PROCESSING = 'PROCESSING', _('Processing')
        COMPLETED = 'COMPLETED', _('Completed')
        FAILED = 'FAILED', _('Failed')
        REFUNDED = 'REFUNDED', _('Refunded')
        PARTIAL_REFUND = 'PARTIAL_REFUND', _('Partially Refunded')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking_reference = models.CharField(
        _('booking reference'),
        max_length=20,
        unique=True,
        blank=True
    )
    
    # User who made the booking
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='bookings'
    )
    
    # Generic foreign key to service (Hotel, Car, Bus, Train)
    service_type = models.CharField(
        _('service type'),
        max_length=20,
        choices=ServiceType.choices
    )
    service_id = models.UUIDField(_('service ID'))
    
    # We'll use content types for the generic relationship
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    object_id = models.UUIDField(null=True, blank=True)
    service_object = GenericForeignKey('content_type', 'object_id')
    
    # Dates
    booking_date = models.DateTimeField(_('booking date'), auto_now_add=True)
    check_in_date = models.DateField(_('check-in date'), null=True, blank=True)
    check_out_date = models.DateField(_('check-out date'), null=True, blank=True)
    travel_date = models.DateField(_('travel date'), null=True, blank=True)
    
    # Passenger/Occupant Details
    quantity = models.PositiveIntegerField(_('quantity'), default=1)  # rooms, cars, tickets
    adults = models.PositiveIntegerField(_('adults'), default=1)
    children = models.PositiveIntegerField(_('children'), default=0)
    
    # Pricing
    base_amount = models.DecimalField(
        _('base amount'),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    tax_amount = models.DecimalField(
        _('tax amount'),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    discount_amount = models.DecimalField(
        _('discount amount'),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total_amount = models.DecimalField(
        _('total amount'),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Status
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    payment_status = models.CharField(
        _('payment status'),
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )
    
    # Contact Information
    contact_name = models.CharField(_('contact name'), max_length=200)
    contact_email = models.EmailField(_('contact email'))
    contact_phone = models.CharField(_('contact phone'), max_length=20)
    
    # Special Requests
    special_requests = models.TextField(_('special requests'), blank=True)
    
    # Cancellation
    cancellation_reason = models.TextField(_('cancellation reason'), blank=True)
    cancellation_date = models.DateTimeField(_('cancellation date'), null=True, blank=True)
    refund_amount = models.DecimalField(
        _('refund amount'),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Metadata for service-specific data
    metadata = models.JSONField(
        _('metadata'),
        default=dict,
        blank=True,
        help_text=_('Service-specific booking details (seats, room numbers, etc.)')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-booking_date']
        verbose_name = _('Booking')
        verbose_name_plural = _('Bookings')
        indexes = [
            models.Index(fields=['booking_reference']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['service_type', 'service_id']),
            models.Index(fields=['booking_date']),
            models.Index(fields=['check_in_date']),
            models.Index(fields=['travel_date']),
        ]
    
    def __str__(self):
        return f"{self.booking_reference} - {self.user.username} - {self.get_service_type_display()}"
    
    def save(self, *args, **kwargs):
        # Generate booking reference if not exists
        if not self.booking_reference:
            self.booking_reference = self.generate_booking_reference()
        
        # Set content type and object_id based on service_type and service_id
        if self.service_type and self.service_id and not self.content_type:
            try:
                # Map service_type to app_label and model
                service_map = {
                    'HOTEL': ('hotels', 'Hotel'),
                    'CAR': ('cars', 'Car'),
                    'BUS': ('buses', 'Bus'),
                    'TRAIN': ('trains', 'Train'),
                }
                
                if self.service_type in service_map:
                    app_label, model_name = service_map[self.service_type]
                    self.content_type = ContentType.objects.get(
                        app_label=app_label,
                        model=model_name.lower()
                    )
                    self.object_id = self.service_id
            except ContentType.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)
    
    def generate_booking_reference(self):
        """Generate unique booking reference."""
        import random
        import string
        
        while True:
            # Generate 8-character alphanumeric reference
            ref = 'BK-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not Booking.objects.filter(booking_reference=ref).exists():
                return ref
    
    @property
    def service_name(self):
        """Get the name of the service."""
        if self.service_object:
            if hasattr(self.service_object, 'name'):
                return self.service_object.name
            elif hasattr(self.service_object, 'train_number'):
                return f"{self.service_object.train_number} - {self.service_object.train_name}"
            elif hasattr(self.service_object, 'bus_number'):
                return self.service_object.bus_number
            elif hasattr(self.service_object, 'registration_number'):
                return f"{self.service_object.brand.name} {self.service_object.model}"
        
        # Fallback to metadata
        return self.metadata.get('service_name', f"{self.get_service_type_display()} Booking")
    
    @property
    def is_upcoming(self):
        """Check if booking is upcoming."""
        if self.status != self.Status.CONFIRMED:
            return False
        
        relevant_date = self.check_in_date or self.travel_date or self.booking_date.date()
        return relevant_date >= timezone.now().date()
    
    @property
    def is_active(self):
        """Check if booking is active (not cancelled or completed)."""
        return self.status in [self.Status.PENDING, self.Status.CONFIRMED, self.Status.RAC, self.Status.WAITLISTED]
    
    @property
    def can_cancel(self):
        """Check if booking can be cancelled."""
        if self.status not in [self.Status.PENDING, self.Status.CONFIRMED, self.Status.RAC, self.Status.WAITLISTED]:
            return False
        
        # Check if within cancellation window
        relevant_date = self.check_in_date or self.travel_date or self.booking_date.date()
        if relevant_date:
            days_before = (relevant_date - timezone.now().date()).days
            return days_before >= 1  # Can cancel at least 1 day before
        
        return True
    
    @property
    def duration_days(self):
        """Calculate duration in days for hotel/car bookings."""
        if self.check_in_date and self.check_out_date:
            return (self.check_out_date - self.check_in_date).days
        return 1
    
    def get_service_details(self):
        """Get service-specific details from metadata."""
        details = {
            'service_type': self.get_service_type_display(),
            'service_name': self.service_name,
            'booking_reference': self.booking_reference,
            'dates': {
                'booking': self.booking_date,
                'check_in': self.check_in_date,
                'check_out': self.check_out_date,
                'travel': self.travel_date,
            },
            'passengers': {
                'adults': self.adults,
                'children': self.children,
                'total': self.adults + self.children,
            },
            'pricing': {
                'base_amount': float(self.base_amount),
                'tax_amount': float(self.tax_amount),
                'discount_amount': float(self.discount_amount),
                'total_amount': float(self.total_amount),
            },
            'status': {
                'booking': self.get_status_display(),
                'payment': self.get_payment_status_display(),
            },
            'contact': {
                'name': self.contact_name,
                'email': self.contact_email,
                'phone': self.contact_phone,
            }
        }
        
        # Add service-specific metadata
        details.update(self.metadata)
        return details
    
    def cancel(self, reason="", refund_percentage=0):
        """Cancel the booking."""
        if not self.can_cancel:
            raise ValueError("Booking cannot be cancelled")
        
        self.status = self.Status.CANCELLED
        self.cancellation_reason = reason
        self.cancellation_date = timezone.now()
        
        # Calculate refund amount
        if refund_percentage > 0:
            self.refund_amount = (self.total_amount * Decimal(refund_percentage)) / 100
        
        self.save()
        
        # Release any reserved resources (seats, rooms, cars)
        self._release_resources()
    
    def _release_resources(self):
        """Release reserved resources (to be implemented by service-specific logic)."""
        # This method should be overridden or called by service-specific cancellation logic
        # For example, in HotelBookingService.cancel_booking()
        pass
    
    def confirm(self):
        """Confirm the booking."""
        if self.status != self.Status.PENDING:
            raise ValueError("Only pending bookings can be confirmed")
        
        self.status = self.Status.CONFIRMED
        self.save()
    
    def mark_completed(self):
        """Mark booking as completed."""
        self.status = self.Status.COMPLETED
        self.save()
    
    def update_payment_status(self, payment_status):
        """Update payment status."""
        self.payment_status = payment_status
        
        # Auto-confirm booking if payment is completed
        if payment_status == self.PaymentStatus.COMPLETED and self.status == self.Status.PENDING:
            self.status = self.Status.CONFIRMED
        
        self.save()
    
    def to_json(self):
        """Convert booking to JSON format."""
        return {
            'id': str(self.id),
            'booking_reference': self.booking_reference,
            'service_type': self.service_type,
            'service_name': self.service_name,
            'user': {
                'id': str(self.user.id),
                'username': self.user.username,
                'email': self.user.email,
            },
            'dates': {
                'booking': self.booking_date.isoformat() if self.booking_date else None,
                'check_in': self.check_in_date.isoformat() if self.check_in_date else None,
                'check_out': self.check_out_date.isoformat() if self.check_out_date else None,
                'travel': self.travel_date.isoformat() if self.travel_date else None,
            },
            'passengers': {
                'adults': self.adults,
                'children': self.children,
            },
            'amount': {
                'base': float(self.base_amount),
                'tax': float(self.tax_amount),
                'discount': float(self.discount_amount),
                'total': float(self.total_amount),
                'refund': float(self.refund_amount),
            },
            'status': {
                'booking': self.status,
                'booking_display': self.get_status_display(),
                'payment': self.payment_status,
                'payment_display': self.get_payment_status_display(),
            },
            'contact': {
                'name': self.contact_name,
                'email': self.contact_email,
                'phone': self.contact_phone,
            },
            'metadata': self.metadata,
            'is_upcoming': self.is_upcoming,
            'can_cancel': self.can_cancel,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class BookingHistory(models.Model):
    """Track changes to bookings."""
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='history'
    )
    
    # Status changes
    old_status = models.CharField(
        _('old status'),
        max_length=20,
        choices=Booking.Status.choices,
        blank=True
    )
    new_status = models.CharField(
        _('new status'),
        max_length=20,
        choices=Booking.Status.choices
    )
    
    # Payment status changes
    old_payment_status = models.CharField(
        _('old payment status'),
        max_length=20,
        choices=Booking.PaymentStatus.choices,
        blank=True
    )
    new_payment_status = models.CharField(
        _('new payment status'),
        max_length=20,
        choices=Booking.PaymentStatus.choices,
        blank=True
    )
    
    # Who made the change
    changed_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='booking_changes'
    )
    
    # Change details
    notes = models.TextField(_('notes'), blank=True)
    metadata = models.JSONField(_('metadata'), default=dict, blank=True)
    
    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Booking History')
        verbose_name_plural = _('Booking Histories')
        indexes = [
            models.Index(fields=['booking', 'created_at']),
        ]
    
    def __str__(self):
        return f"History for {self.booking.booking_reference} - {self.created_at}"
    
    @classmethod
    def log_status_change(cls, booking, old_status, new_status, user=None, notes=""):
        """Log a status change."""
        return cls.objects.create(
            booking=booking,
            old_status=old_status,
            new_status=new_status,
            changed_by=user,
            notes=notes
        )
    
    @classmethod
    def log_payment_status_change(cls, booking, old_status, new_status, user=None, notes=""):
        """Log a payment status change."""
        return cls.objects.create(
            booking=booking,
            old_payment_status=old_status,
            new_payment_status=new_status,
            changed_by=user,
            notes=notes
        )


class BookingDocument(models.Model):
    """Documents related to bookings (tickets, invoices, receipts)."""
    
    class DocumentType(models.TextChoices):
        TICKET = 'TICKET', _('Ticket')
        INVOICE = 'INVOICE', _('Invoice')
        RECEIPT = 'RECEIPT', _('Receipt')
        CONFIRMATION = 'CONFIRMATION', _('Confirmation')
        CANCELLATION = 'CANCELLATION', _('Cancellation')
        ID_PROOF = 'ID_PROOF', _('ID Proof')
        OTHER = 'OTHER', _('Other')
    
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    
    document_type = models.CharField(
        _('document type'),
        max_length=20,
        choices=DocumentType.choices
    )
    name = models.CharField(_('document name'), max_length=200)
    description = models.TextField(_('description'), blank=True)
    
    # File storage
    file = models.FileField(
        _('file'),
        upload_to='bookings/documents/%Y/%m/%d/'
    )
    
    # Status
    is_verified = models.BooleanField(_('is verified'), default=False)
    
    # Upload info
    uploaded_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_documents'
    )
    
    # Metadata
    metadata = models.JSONField(_('metadata'), default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Booking Document')
        verbose_name_plural = _('Booking Documents')
        indexes = [
            models.Index(fields=['booking', 'document_type']),
            models.Index(fields=['is_verified']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.booking.booking_reference}"
    
    @property
    def file_url(self):
        """Get file URL."""
        return self.file.url if self.file else None
    
    @property
    def file_name(self):
        """Get original file name."""
        if self.file:
            return self.file.name.split('/')[-1]
        return None
    
    @property
    def file_size(self):
        """Get file size in KB."""
        if self.file and hasattr(self.file, 'size'):
            return self.file.size / 1024  # KB
        return 0


class BookingNotification(models.Model):
    """Notifications related to bookings."""
    
    class NotificationType(models.TextChoices):
        CONFIRMATION = 'CONFIRMATION', _('Booking Confirmation')
        CANCELLATION = 'CANCELLATION', _('Booking Cancellation')
        REMINDER = 'REMINDER', _('Reminder')
        PAYMENT = 'PAYMENT', _('Payment Notification')
        STATUS_UPDATE = 'STATUS_UPDATE', _('Status Update')
        PROMOTIONAL = 'PROMOTIONAL', _('Promotional')
    
    class NotificationChannel(models.TextChoices):
        EMAIL = 'EMAIL', _('Email')
        SMS = 'SMS', _('SMS')
        PUSH = 'PUSH', _('Push Notification')
        IN_APP = 'IN_APP', _('In-App Notification')
    
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='booking_notifications'
    )
    
    notification_type = models.CharField(
        _('notification type'),
        max_length=20,
        choices=NotificationType.choices
    )
    channel = models.CharField(
        _('channel'),
        max_length=20,
        choices=NotificationChannel.choices
    )
    
    # Content
    subject = models.CharField(_('subject'), max_length=200)
    message = models.TextField(_('message'))
    metadata = models.JSONField(_('metadata'), default=dict, blank=True)
    
    # Status
    is_sent = models.BooleanField(_('is sent'), default=False)
    is_read = models.BooleanField(_('is read'), default=False)
    sent_at = models.DateTimeField(_('sent at'), null=True, blank=True)
    read_at = models.DateTimeField(_('read at'), null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Booking Notification')
        verbose_name_plural = _('Booking Notifications')
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['booking', 'notification_type']),
            models.Index(fields=['is_sent']),
        ]
    
    def __str__(self):
        return f"{self.get_notification_type_display()} - {self.booking.booking_reference}"
    
    def mark_as_sent(self):
        """Mark notification as sent."""
        from django.utils import timezone
        self.is_sent = True
        self.sent_at = timezone.now()
        self.save()
    
    def mark_as_read(self):
        """Mark notification as read."""
        from django.utils import timezone
        self.is_read = True
        self.read_at = timezone.now()
        self.save()


class BookingSettings(models.Model):
    """Settings for booking system."""
    
    class CancellationPolicy(models.TextChoices):
        FLEXIBLE = 'FLEXIBLE', _('Flexible - Free cancellation up to 24 hours')
        MODERATE = 'MODERATE', _('Moderate - Free cancellation up to 48 hours')
        STRICT = 'STRICT', _('Strict - Free cancellation up to 7 days')
        NON_REFUNDABLE = 'NON_REFUNDABLE', _('Non-refundable')
    
    # Cancellation settings
    default_cancellation_policy = models.CharField(
        _('default cancellation policy'),
        max_length=20,
        choices=CancellationPolicy.choices,
        default=CancellationPolicy.MODERATE
    )
    
    # Booking window
    max_advance_booking_days = models.PositiveIntegerField(
        _('maximum advance booking days'),
        default=365,
        help_text=_('Maximum days in advance a booking can be made')
    )
    min_advance_booking_hours = models.PositiveIntegerField(
        _('minimum advance booking hours'),
        default=2,
        help_text=_('Minimum hours before service for booking')
    )
    
    # Payment settings
    payment_timeout_minutes = models.PositiveIntegerField(
        _('payment timeout minutes'),
        default=30,
        help_text=_('Minutes before pending booking is cancelled')
    )
    auto_cancel_unpaid = models.BooleanField(
        _('auto cancel unpaid bookings'),
        default=True,
        help_text=_('Automatically cancel bookings if payment not completed')
    )
    
    # Notification settings
    send_booking_confirmation = models.BooleanField(
        _('send booking confirmation'),
        default=True
    )
    send_reminder_before = models.PositiveIntegerField(
        _('send reminder before hours'),
        default=24,
        help_text=_('Hours before service to send reminder')
    )
    
    # Commission/fees
    service_fee_percentage = models.DecimalField(
        _('service fee percentage'),
        max_digits=5,
        decimal_places=2,
        default=5.00,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    tax_percentage = models.DecimalField(
        _('tax percentage'),
        max_digits=5,
        decimal_places=2,
        default=10.00,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Metadata
    metadata = models.JSONField(_('metadata'), default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Booking Settings')
        verbose_name_plural = _('Booking Settings')
    
    def __str__(self):
        return "Booking Settings"
    
    @classmethod
    def get_settings(cls):
        """Get or create settings singleton."""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj
    
    def save(self, *args, **kwargs):
        """Ensure only one settings instance."""
        self.pk = 1
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Prevent deletion of settings."""
        pass


# Signals for booking
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver


@receiver(pre_save, sender=Booking)
def booking_pre_save(sender, instance, **kwargs):
    """Handle booking pre-save."""
    if not instance.booking_reference:
        instance.booking_reference = instance.generate_booking_reference()
    
    # Calculate total amount if not set
    if instance.base_amount and instance.tax_amount and instance.discount_amount:
        if instance.total_amount == Decimal('0.00'):
            instance.total_amount = instance.base_amount + instance.tax_amount - instance.discount_amount


@receiver(post_save, sender=Booking)
def booking_post_save(sender, instance, created, **kwargs):
    """Handle booking post-save."""
    if created:
        # Create initial history entry
        BookingHistory.objects.create(
            booking=instance,
            new_status=instance.status,
            new_payment_status=instance.payment_status,
            notes="Booking created",
            metadata={'created_by': 'system'}
        )
        
        # Send confirmation notification if enabled
        settings = BookingSettings.get_settings()
        if settings.send_booking_confirmation:
            BookingNotification.objects.create(
                booking=instance,
                user=instance.user,
                notification_type=BookingNotification.NotificationType.CONFIRMATION,
                channel=BookingNotification.NotificationChannel.EMAIL,
                subject=f"Booking Confirmation - {instance.booking_reference}",
                message=f"Your {instance.get_service_type_display()} booking has been created.",
                metadata={'booking_reference': instance.booking_reference}
            )
    else:
        # Check for status changes
        if 'status' in instance.tracker.changed():
            BookingHistory.log_status_change(
                booking=instance,
                old_status=instance.tracker.previous('status'),
                new_status=instance.status,
                notes=f"Status changed from {instance.tracker.previous('status')} to {instance.status}"
            )
        
        # Check for payment status changes
        if 'payment_status' in instance.tracker.changed():
            BookingHistory.log_payment_status_change(
                booking=instance,
                old_status=instance.tracker.previous('payment_status'),
                new_status=instance.payment_status,
                notes=f"Payment status changed from {instance.tracker.previous('payment_status')} to {instance.payment_status}"
            )


# FieldTracker for tracking changes
# from model_utils import FieldTracker


# # Add tracker to Booking model
# Booking.add_to_class('tracker', FieldTracker())
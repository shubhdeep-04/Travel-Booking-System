"""
Payment Management Models for Travel Booking System.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid

class Payment(models.Model):
    """Payment model for bookings."""
    
    class PaymentMethod(models.TextChoices):
        CREDIT_CARD = 'CREDIT_CARD', _('Credit Card')
        DEBIT_CARD = 'DEBIT_CARD', _('Debit Card')
        NET_BANKING = 'NET_BANKING', _('Net Banking')
        UPI = 'UPI', _('UPI')
        WALLET = 'WALLET', _('Wallet')
        CASH = 'CASH', _('Cash')
        BANK_TRANSFER = 'BANK_TRANSFER', _('Bank Transfer')
    
    class PaymentStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        PROCESSING = 'PROCESSING', _('Processing')
        COMPLETED = 'COMPLETED', _('Completed')
        FAILED = 'FAILED', _('Failed')
        REFUNDED = 'REFUNDED', _('Refunded')
        PARTIALLY_REFUNDED = 'PARTIALLY_REFUNDED', _('Partially Refunded')
        CANCELLED = 'CANCELLED', _('Cancelled')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.ForeignKey(
        'bookings.Booking',
        on_delete=models.CASCADE,
        related_name='payments'
    )
    
    # Payment details
    payment_reference = models.CharField(
        _('payment reference'),
        max_length=50,
        unique=True,
        blank=True
    )
    external_payment_id = models.CharField(
        _('external payment ID'),
        max_length=100,
        blank=True,
        help_text=_('Payment gateway transaction ID')
    )
    
    # Amount details
    amount = models.DecimalField(
        _('amount'),
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    currency = models.CharField(
        _('currency'),
        max_length=3,
        default='USD'
    )
    
    # Payment method
    payment_method = models.CharField(
        _('payment method'),
        max_length=20,
        choices=PaymentMethod.choices
    )
    payment_gateway = models.CharField(
        _('payment gateway'),
        max_length=50,
        blank=True,
        help_text=_('e.g., Stripe, PayPal, Razorpay')
    )
    
    # Status
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )
    
    # Card details (masked, for reference only)
    card_last4 = models.CharField(_('card last 4 digits'), max_length=4, blank=True)
    card_brand = models.CharField(_('card brand'), max_length=20, blank=True)
    
    # UPI details
    upi_id = models.CharField(_('UPI ID'), max_length=50, blank=True)
    
    # Bank details
    bank_name = models.CharField(_('bank name'), max_length=100, blank=True)
    account_last4 = models.CharField(_('account last 4 digits'), max_length=4, blank=True)
    
    # Metadata
    metadata = models.JSONField(
        _('metadata'),
        default=dict,
        blank=True,
        help_text=_('Additional payment details')
    )
    
    # Timestamps
    initiated_at = models.DateTimeField(_('initiated at'), auto_now_add=True)
    completed_at = models.DateTimeField(_('completed at'), null=True, blank=True)
    failed_at = models.DateTimeField(_('failed at'), null=True, blank=True)
    refunded_at = models.DateTimeField(_('refunded at'), null=True, blank=True)
    
    class Meta:
        ordering = ['-initiated_at']
        verbose_name = _('Payment')
        verbose_name_plural = _('Payments')
        indexes = [
            models.Index(fields=['booking', 'status']),
            models.Index(fields=['payment_reference']),
            models.Index(fields=['external_payment_id']),
            models.Index(fields=['initiated_at']),
        ]
    
    def __str__(self):
        return f"{self.payment_reference} - {self.booking.booking_reference} - {self.amount}"
    
    def save(self, *args, **kwargs):
        # Generate payment reference if not exists
        if not self.payment_reference:
            self.payment_reference = self.generate_payment_reference()
        
        super().save(*args, **kwargs)
    
    def generate_payment_reference(self):
        """Generate unique payment reference."""
        import random
        import string
        
        while True:
            # Generate 10-character alphanumeric reference
            ref = 'PAY-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
            if not Payment.objects.filter(payment_reference=ref).exists():
                return ref
    
    @property
    def is_successful(self):
        """Check if payment was successful."""
        return self.status in [self.PaymentStatus.COMPLETED, self.PaymentStatus.REFUNDED]
    
    @property
    def is_refundable(self):
        """Check if payment can be refunded."""
        return self.status == self.PaymentStatus.COMPLETED and self.amount > 0
    
    def mark_completed(self, external_id='', metadata=None):
        """Mark payment as completed."""
        from django.utils import timezone
        
        self.status = self.PaymentStatus.COMPLETED
        self.external_payment_id = external_id
        self.completed_at = timezone.now()
        
        if metadata:
            self.metadata.update(metadata)
        
        self.save()
        
        # Update booking status
        self.booking.status = 'CONFIRMED'
        self.booking.save()
    
    def mark_failed(self, reason='', metadata=None):
        """Mark payment as failed."""
        from django.utils import timezone
        
        self.status = self.PaymentStatus.FAILED
        self.failed_at = timezone.now()
        
        if metadata:
            self.metadata.update({'failure_reason': reason, **metadata})
        
        self.save()
        
        # Update booking status
        self.booking.status = 'FAILED'
        self.booking.save()
    
    def initiate_refund(self, amount=None, reason=''):
        """Initiate refund for payment."""
        from django.utils import timezone
        
        if not self.is_refundable:
            raise ValueError("Payment is not refundable")
        
        refund_amount = amount or self.amount
        
        if refund_amount > self.amount:
            raise ValueError("Refund amount cannot exceed payment amount")
        
        # Create refund record
        refund = Refund.objects.create(
            payment=self,
            amount=refund_amount,
            reason=reason,
            status=Refund.RefundStatus.PENDING
        )
        
        # Update payment status
        if refund_amount == self.amount:
            self.status = self.PaymentStatus.REFUNDED
        else:
            self.status = self.PaymentStatus.PARTIALLY_REFUNDED
        
        self.refunded_at = timezone.now()
        self.save()
        
        return refund


class Refund(models.Model):
    """Refund model for payments."""
    
    class RefundMethod(models.TextChoices):
        ORIGINAL = 'ORIGINAL', _('Original Payment Method')
        WALLET = 'WALLET', _('Wallet Credit')
        BANK_TRANSFER = 'BANK_TRANSFER', _('Bank Transfer')
        CASH = 'CASH', _('Cash')
    
    class RefundStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        PROCESSING = 'PROCESSING', _('Processing')
        COMPLETED = 'COMPLETED', _('Completed')
        FAILED = 'FAILED', _('Failed')
        CANCELLED = 'CANCELLED', _('Cancelled')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='refunds'
    )
    
    # Refund details
    refund_reference = models.CharField(
        _('refund reference'),
        max_length=50,
        unique=True,
        blank=True
    )
    external_refund_id = models.CharField(
        _('external refund ID'),
        max_length=100,
        blank=True
    )
    
    # Amount details
    amount = models.DecimalField(
        _('amount'),
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    # Refund method
    refund_method = models.CharField(
        _('refund method'),
        max_length=20,
        choices=RefundMethod.choices,
        default=RefundMethod.ORIGINAL
    )
    
    # Status
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=RefundStatus.choices,
        default=RefundStatus.PENDING
    )
    
    # Reason
    reason = models.TextField(_('reason'), blank=True)
    
    # Metadata
    metadata = models.JSONField(
        _('metadata'),
        default=dict,
        blank=True
    )
    
    # Timestamps
    requested_at = models.DateTimeField(_('requested at'), auto_now_add=True)
    processed_at = models.DateTimeField(_('processed at'), null=True, blank=True)
    completed_at = models.DateTimeField(_('completed at'), null=True, blank=True)
    
    class Meta:
        ordering = ['-requested_at']
        verbose_name = _('Refund')
        verbose_name_plural = _('Refunds')
        indexes = [
            models.Index(fields=['payment', 'status']),
            models.Index(fields=['refund_reference']),
        ]
    
    def __str__(self):
        return f"{self.refund_reference} - {self.payment.payment_reference} - {self.amount}"
    
    def save(self, *args, **kwargs):
        # Generate refund reference if not exists
        if not self.refund_reference:
            self.refund_reference = self.generate_refund_reference()
        
        super().save(*args, **kwargs)
    
    def generate_refund_reference(self):
        """Generate unique refund reference."""
        import random
        import string
        
        while True:
            # Generate 8-character alphanumeric reference
            ref = 'REF-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not Refund.objects.filter(refund_reference=ref).exists():
                return ref
    
    def mark_completed(self, external_id='', metadata=None):
        """Mark refund as completed."""
        from django.utils import timezone
        
        self.status = self.RefundStatus.COMPLETED
        self.external_refund_id = external_id
        self.completed_at = timezone.now()
        
        if metadata:
            self.metadata.update(metadata)
        
        self.save()
    
    def mark_failed(self, reason='', metadata=None):
        """Mark refund as failed."""
        from django.utils import timezone
        
        self.status = self.RefundStatus.FAILED
        self.processed_at = timezone.now()
        
        if metadata:
            self.metadata.update({'failure_reason': reason, **metadata})
        
        self.save()


class Transaction(models.Model):
    """Transaction log for all financial activities."""
    
    class TransactionType(models.TextChoices):
        PAYMENT = 'PAYMENT', _('Payment')
        REFUND = 'REFUND', _('Refund')
        COMMISSION = 'COMMISSION', _('Commission')
        FEE = 'FEE', _('Fee')
        ADJUSTMENT = 'ADJUSTMENT', _('Adjustment')
    
    class TransactionStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        COMPLETED = 'COMPLETED', _('Completed')
        FAILED = 'FAILED', _('Failed')
        REVERSED = 'REVERSED', _('Reversed')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    booking = models.ForeignKey(
        'bookings.Booking',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )
    payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )
    refund = models.ForeignKey(
        Refund,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )
    
    # Transaction details
    transaction_reference = models.CharField(
        _('transaction reference'),
        max_length=50,
        unique=True,
        blank=True
    )
    transaction_type = models.CharField(
        _('transaction type'),
        max_length=20,
        choices=TransactionType.choices
    )
    
    # Amount details
    amount = models.DecimalField(
        _('amount'),
        max_digits=12,
        decimal_places=2
    )
    currency = models.CharField(
        _('currency'),
        max_length=3,
        default='USD'
    )
    
    # Status
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=TransactionStatus.choices,
        default=TransactionStatus.PENDING
    )
    
    # Description
    description = models.TextField(_('description'), blank=True)
    
    # Metadata
    metadata = models.JSONField(
        _('metadata'),
        default=dict,
        blank=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(_('completed at'), null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Transaction')
        verbose_name_plural = _('Transactions')
        indexes = [
            models.Index(fields=['user', 'transaction_type']),
            models.Index(fields=['booking', 'status']),
            models.Index(fields=['transaction_reference']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.transaction_reference} - {self.user.username} - {self.amount}"
    
    def save(self, *args, **kwargs):
        # Generate transaction reference if not exists
        if not self.transaction_reference:
            self.transaction_reference = self.generate_transaction_reference()
        
        super().save(*args, **kwargs)
    
    def generate_transaction_reference(self):
        """Generate unique transaction reference."""
        import random
        import string
        
        while True:
            # Generate 12-character alphanumeric reference
            ref = 'TXN-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
            if not Transaction.objects.filter(transaction_reference=ref).exists():
                return ref


class Wallet(models.Model):
    """User wallet for credits and refunds."""
    user = models.OneToOneField(
        'users.User',
        on_delete=models.CASCADE,
        related_name='wallet'
    )
    balance = models.DecimalField(
        _('balance'),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    currency = models.CharField(
        _('currency'),
        max_length=3,
        default='USD'
    )
    
    # Status
    is_active = models.BooleanField(_('is active'), default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Wallet')
        verbose_name_plural = _('Wallets')
    
    def __str__(self):
        return f"Wallet - {self.user.username} - {self.balance}"
    
    def credit(self, amount, source='', description=''):
        """Credit amount to wallet."""
        from django.utils import timezone
        
        if amount <= 0:
            raise ValueError("Credit amount must be positive")
        
        self.balance += amount
        self.save()
        
        # Create wallet transaction
        WalletTransaction.objects.create(
            wallet=self,
            amount=amount,
            transaction_type='CREDIT',
            source=source,
            description=description,
            balance_after=self.balance
        )
    
    def debit(self, amount, source='', description=''):
        """Debit amount from wallet."""
        from django.utils import timezone
        
        if amount <= 0:
            raise ValueError("Debit amount must be positive")
        
        if amount > self.balance:
            raise ValueError("Insufficient wallet balance")
        
        self.balance -= amount
        self.save()
        
        # Create wallet transaction
        WalletTransaction.objects.create(
            wallet=self,
            amount=amount,
            transaction_type='DEBIT',
            source=source,
            description=description,
            balance_after=self.balance
        )
    
    def can_pay(self, amount):
        """Check if wallet has sufficient balance."""
        return self.balance >= amount


class WalletTransaction(models.Model):
    """Wallet transaction history."""
    
    class TransactionType(models.TextChoices):
        CREDIT = 'CREDIT', _('Credit')
        DEBIT = 'DEBIT', _('Debit')
    
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(_('amount'), max_digits=12, decimal_places=2)
    transaction_type = models.CharField(
        _('transaction type'),
        max_length=10,
        choices=TransactionType.choices
    )
    source = models.CharField(_('source'), max_length=100, blank=True)
    description = models.TextField(_('description'), blank=True)
    balance_before = models.DecimalField(
        _('balance before'),
        max_digits=12,
        decimal_places=2
    )
    balance_after = models.DecimalField(
        _('balance after'),
        max_digits=12,
        decimal_places=2
    )
    reference_id = models.CharField(_('reference ID'), max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Wallet Transaction')
        verbose_name_plural = _('Wallet Transactions')
    
    def __str__(self):
        return f"{self.transaction_type} - {self.wallet.user.username} - {self.amount}"
    
    def save(self, *args, **kwargs):
        if not self.balance_before:
            self.balance_before = self.wallet.balance - (
                self.amount if self.transaction_type == 'CREDIT' else -self.amount
            )
        super().save(*args, **kwargs)
"""
Utilities for payment operations.
"""

from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import hashlib
import hmac
import json
from typing import Dict, Tuple, Optional
import uuid

logger = logging.getLogger(__name__)


class PaymentProcessor:
    """Process payments and handle payment gateway integration."""
    
    def __init__(self):
        # In production, load configuration from settings
        self.gateways = {
            'STRIPE': {
                'api_key': 'sk_test_...',  # Load from settings
                'webhook_secret': 'whsec_...',
            },
            'PAYPAL': {
                'client_id': '...',
                'client_secret': '...',
            },
            'RAZORPAY': {
                'key_id': '...',
                'key_secret': '...',
            },
        }
    
    def process_payment(
        self,
        amount: Decimal,
        payment_method: str,
        gateway: str = '',
        metadata: Dict = None
    ) -> Tuple[bool, str, str]:
        """
        Process payment through payment gateway.
        Returns: (success, transaction_id, error_message)
        """
        # This is a simulation for demo purposes
        # In production, integrate with actual payment gateways
        
        try:
            # Simulate payment processing
            transaction_id = f"TXN-{uuid.uuid4().hex[:16].upper()}"
            
            # Simulate different outcomes based on amount (for demo)
            if amount <= 0:
                return False, '', "Invalid amount"
            
            # 90% success rate for demo
            import random
            if random.random() < 0.9:  # 90% success rate
                logger.info(f"Payment processed successfully: {transaction_id}")
                return True, transaction_id, ""
            else:
                # Simulate failure
                failure_reasons = [
                    "Insufficient funds",
                    "Card declined",
                    "Network error",
                    "Timeout",
                    "Invalid payment method",
                ]
                error = random.choice(failure_reasons)
                logger.warning(f"Payment failed: {error}")
                return False, '', error
                
        except Exception as e:
            logger.error(f"Payment processing error: {str(e)}")
            return False, '', f"Payment processing failed: {str(e)}"
    
    def process_wallet_payment(
        self,
        user,
        amount: Decimal,
        description: str = ''
    ) -> Tuple[bool, str, str]:
        """
        Process payment using wallet balance.
        Returns: (success, transaction_id, error_message)
        """
        from .models import Wallet
        
        try:
            # Get user wallet
            wallet, created = Wallet.objects.get_or_create(
                user=user,
                defaults={'balance': Decimal('0.00')}
            )
            
            # Check balance
            if not wallet.can_pay(amount):
                return False, '', "Insufficient wallet balance"
            
            # Debit from wallet
            with transaction.atomic():
                wallet.debit(
                    amount,
                    source='Booking Payment',
                    description=description
                )
                
                transaction_id = f"WALLET-{uuid.uuid4().hex[:12].upper()}"
                
                logger.info(f"Wallet payment processed: {transaction_id}")
                return True, transaction_id, ""
                
        except Exception as e:
            logger.error(f"Wallet payment error: {str(e)}")
            return False, '', f"Wallet payment failed: {str(e)}"
    
    def process_refund(
        self,
        amount: Decimal,
        refund_method: str,
        description: str = ''
    ) -> Tuple[bool, str, str]:
        """
        Process refund.
        Returns: (success, transaction_id, error_message)
        """
        # This is a simulation for demo purposes
        
        try:
            # Simulate refund processing
            transaction_id = f"REF-{uuid.uuid4().hex[:12].upper()}"
            
            # Simulate processing delay
            import time
            time.sleep(1)  # Simulate API call
            
            logger.info(f"Refund processed: {transaction_id}")
            return True, transaction_id, ""
            
        except Exception as e:
            logger.error(f"Refund processing error: {str(e)}")
            return False, '', f"Refund processing failed: {str(e)}"
    
    def handle_webhook(self, data: Dict) -> bool:
        """Handle payment gateway webhooks."""
        try:
            # Determine gateway from webhook data
            gateway = data.get('gateway', '')
            event_type = data.get('event_type', '')
            event_data = data.get('data', {})
            
            if gateway == 'STRIPE':
                return self._handle_stripe_webhook(event_type, event_data)
            elif gateway == 'PAYPAL':
                return self._handle_paypal_webhook(event_type, event_data)
            elif gateway == 'RAZORPAY':
                return self._handle_razorpay_webhook(event_type, event_data)
            else:
                logger.warning(f"Unknown gateway webhook: {gateway}")
                return False
                
        except Exception as e:
            logger.error(f"Webhook handling error: {str(e)}")
            return False
    
    def _handle_stripe_webhook(self, event_type: str, data: Dict) -> bool:
        """Handle Stripe webhook events."""
        from .models import Payment
        
        try:
            if event_type == 'payment_intent.succeeded':
                payment_intent = data.get('payment_intent', {})
                payment_id = payment_intent.get('metadata', {}).get('payment_id')
                
                if payment_id:
                    payment = Payment.objects.get(id=payment_id)
                    payment.mark_completed(
                        external_id=payment_intent.get('id', ''),
                        metadata={'stripe_event': event_type}
                    )
                    return True
            
            elif event_type == 'payment_intent.payment_failed':
                payment_intent = data.get('payment_intent', {})
                payment_id = payment_intent.get('metadata', {}).get('payment_id')
                
                if payment_id:
                    payment = Payment.objects.get(id=payment_id)
                    error = payment_intent.get('last_payment_error', {}).get('message', '')
                    payment.mark_failed(
                        reason=error,
                        metadata={'stripe_event': event_type}
                    )
                    return True
            
            elif event_type == 'charge.refunded':
                charge = data.get('charge', {})
                payment_id = charge.get('metadata', {}).get('payment_id')
                
                if payment_id:
                    # Handle refund completion
                    pass
            
            return False
            
        except Payment.DoesNotExist:
            logger.error(f"Payment not found for webhook: {event_type}")
            return False
        except Exception as e:
            logger.error(f"Stripe webhook error: {str(e)}")
            return False
    
    def _handle_paypal_webhook(self, event_type: str, data: Dict) -> bool:
        """Handle PayPal webhook events."""
        # Implementation for PayPal
        return True
    
    def _handle_razorpay_webhook(self, event_type: str, data: Dict) -> bool:
        """Handle Razorpay webhook events."""
        # Implementation for Razorpay
        return True
    
    def verify_webhook_signature(self, payload: bytes, signature: str, secret: str) -> bool:
        """Verify webhook signature."""
        try:
            # For Stripe
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            logger.error(f"Signature verification error: {str(e)}")
            return False


class PaymentAnalytics:
    """Analytics for payment data."""
    
    @staticmethod
    def get_payment_stats(start_date: datetime.date, end_date: datetime.date) -> Dict:
        """Get payment statistics for a period."""
        from .models import Payment
        from django.db.models import Count, Sum, Avg
        
        payments = Payment.objects.filter(
            initiated_at__date__range=[start_date, end_date]
        )
        
        stats = payments.aggregate(
            total_payments=Count('id'),
            total_amount=Sum('amount', filter=models.Q(status='COMPLETED')),
            avg_payment=Avg('amount', filter=models.Q(status='COMPLETED')),
            success_rate=Count('id', filter=models.Q(status='COMPLETED')) * 100.0 / Count('id') if Count('id') > 0 else 0,
        )
        
        # Payment method breakdown
        method_breakdown = list(payments.values('payment_method').annotate(
            count=Count('id'),
            amount=Sum('amount')
        ).order_by('-count'))
        
        # Status breakdown
        status_breakdown = list(payments.values('status').annotate(
            count=Count('id'),
            percentage=Count('id') * 100.0 / payments.count()
        ).order_by('-count'))
        
        # Daily trends
        daily_trends = list(payments.extra(
            select={'day': 'DATE(initiated_at)'}
        ).values('day').annotate(
            payments=Count('id'),
            amount=Sum('amount')
        ).order_by('day'))
        
        return {
            'period': {
                'start': start_date,
                'end': end_date,
            },
            'summary': stats,
            'method_breakdown': method_breakdown,
            'status_breakdown': status_breakdown,
            'daily_trends': daily_trends,
        }
    
    @staticmethod
    def get_revenue_forecast(
        start_date: datetime.date,
        end_date: datetime.date,
        historical_days: int = 90
    ) -> Dict:
        """Forecast revenue based on historical data."""
        from .models import Payment
        from django.db.models import Sum, Avg
        
        # Get historical data
        history_start = start_date - timedelta(days=historical_days)
        historical_payments = Payment.objects.filter(
            initiated_at__date__range=[history_start, start_date - timedelta(days=1)],
            status='COMPLETED'
        )
        
        # Calculate average daily revenue
        avg_daily_revenue = historical_payments.aggregate(
            avg=Avg('amount')
        )['avg'] or Decimal('0.00')
        
        # Calculate forecast
        days = (end_date - start_date).days + 1
        forecast_revenue = avg_daily_revenue * days
        
        # Growth rate (simplified)
        # In production, use time series forecasting
        growth_rate = Decimal('0.05')  # 5% growth
        
        forecast_with_growth = forecast_revenue * (1 + growth_rate)
        
        return {
            'forecast_period': {
                'start': start_date,
                'end': end_date,
                'days': days,
            },
            'historical_days': historical_days,
            'avg_daily_revenue': avg_daily_revenue,
            'forecast_revenue': forecast_revenue,
            'forecast_with_growth': forecast_with_growth,
            'growth_rate': growth_rate,
            'confidence_level': 0.85,  # 85% confidence
        }


class PaymentValidator:
    """Validate payment data and constraints."""
    
    @staticmethod
    def validate_payment_amount(amount: Decimal, booking_amount: Decimal) -> Tuple[bool, str]:
        """Validate payment amount against booking amount."""
        if amount <= 0:
            return False, "Payment amount must be positive"
        
        if amount > booking_amount * Decimal('1.1'):  # Allow 10% overpayment
            return False, f"Payment amount cannot exceed ${booking_amount * Decimal('1.1'):.2f}"
        
        return True, ""
    
    @staticmethod
    def validate_payment_method(method: str, available_methods: list = None) -> Tuple[bool, str]:
        """Validate payment method."""
        from .models import Payment
        
        valid_methods = [choice[0] for choice in Payment.PaymentMethod.choices]
        
        if method not in valid_methods:
            return False, f"Invalid payment method. Valid methods: {', '.join(valid_methods)}"
        
        if available_methods and method not in available_methods:
            return False, f"Payment method not available. Available methods: {', '.join(available_methods)}"
        
        return True, ""
    
    @staticmethod
    def validate_card_details(
        card_number: str,
        expiry_month: int,
        expiry_year: int,
        cvv: str
    ) -> Tuple[bool, str]:
        """Validate card details."""
        # Basic validation (in production, use proper validation)
        
        # Check card number length
        if not (13 <= len(card_number.replace(' ', '')) <= 19):
            return False, "Invalid card number length"
        
        # Check expiry date
        from datetime import date
        current_year = date.today().year
        current_month = date.today().month
        
        if expiry_year < current_year or (expiry_year == current_year and expiry_month < current_month):
            return False, "Card has expired"
        
        # Check CVV
        if len(cvv) not in [3, 4]:
            return False, "Invalid CVV length"
        
        # Luhn algorithm check (simplified)
        if not PaymentValidator._luhn_check(card_number.replace(' ', '')):
            return False, "Invalid card number"
        
        return True, ""
    
    @staticmethod
    def _luhn_check(card_number: str) -> bool:
        """Luhn algorithm for card number validation."""
        def digits_of(n):
            return [int(d) for d in str(n)]
        
        digits = digits_of(card_number)
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        
        checksum = sum(odd_digits)
        
        for d in even_digits:
            checksum += sum(digits_of(d * 2))
        
        return checksum % 10 == 0
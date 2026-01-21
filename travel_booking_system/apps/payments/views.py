"""
Views for Payment operations.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import CreateView, DetailView, ListView, TemplateView
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import datetime, timedelta
import json

from .models import Payment, Refund, Transaction, Wallet, WalletTransaction
from .forms import PaymentForm, RefundRequestForm
from .utils import PaymentProcessor


class CreatePaymentView(LoginRequiredMixin, CreateView):
    """Create a new payment for a booking."""
    model = Payment
    form_class = PaymentForm
    template_name = 'payments/create_payment.html'
    
    def get_initial(self):
        initial = super().get_initial()
        
        # Get booking from session
        pending_booking = self.request.session.get('pending_booking')
        if pending_booking:
            from apps.bookings.models import Booking
            try:
                booking = Booking.objects.get(
                    id=pending_booking['booking_id'],
                    user=self.request.user
                )
                initial.update({
                    'booking': booking,
                    'amount': booking.total_amount,
                })
            except Booking.DoesNotExist:
                pass
        
        return initial
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get pending booking from session
        pending_booking = self.request.session.get('pending_booking')
        if pending_booking:
            context['pending_booking'] = pending_booking
        
        # Get wallet balance if exists
        try:
            wallet = Wallet.objects.get(user=self.request.user)
            context['wallet_balance'] = wallet.balance
        except Wallet.DoesNotExist:
            context['wallet_balance'] = 0
        
        return context
    
    def form_valid(self, form):
        booking = form.cleaned_data['booking']
        
        # Validate booking belongs to user
        if booking.user != self.request.user:
            messages.error(self.request, _('Invalid booking.'))
            return self.form_invalid(form)
        
        # Validate booking status
        if booking.status != 'PENDING':
            messages.error(self.request, _('Booking is not in pending state.'))
            return self.form_invalid(form)
        
        # Create payment
        payment = form.save(commit=False)
        payment.booking = booking
        payment.amount = booking.total_amount
        
        # Process payment
        payment_method = form.cleaned_data['payment_method']
        payment_gateway = form.cleaned_data.get('payment_gateway', '')
        card_last4 = form.cleaned_data.get('card_last4', '')
        
        # Initialize payment processor
        processor = PaymentProcessor()
        
        # Process payment based on method
        if payment_method == 'WALLET':
            # Process wallet payment
            success, transaction_id, error = processor.process_wallet_payment(
                self.request.user,
                payment.amount,
                f"Booking {booking.booking_reference}"
            )
        else:
            # Process external payment (simulated for demo)
            success, transaction_id, error = processor.process_payment(
                payment.amount,
                payment_method,
                payment_gateway,
                {
                    'user_id': str(self.request.user.id),
                    'booking_id': str(booking.id),
                    'card_last4': card_last4,
                }
            )
        
        if success:
            # Update payment
            payment.external_payment_id = transaction_id
            payment.status = 'COMPLETED'
            payment.completed_at = timezone.now()
            payment.save()
            
            # Update booking status
            booking.status = 'CONFIRMED'
            booking.save()
            
            # Clear pending booking from session
            if 'pending_booking' in self.request.session:
                del self.request.session['pending_booking']
            
            messages.success(
                self.request,
                _(f'Payment successful! Payment Reference: {payment.payment_reference}')
            )
            
            # Redirect to booking detail
            return redirect('bookings:booking_detail', pk=booking.id)
        else:
            messages.error(self.request, _(f'Payment failed: {error}'))
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, _('Please correct the errors below.'))
        return super().form_invalid(form)


class PaymentDetailView(LoginRequiredMixin, DetailView):
    """View payment details."""
    model = Payment
    template_name = 'payments/payment_detail.html'
    context_object_name = 'payment'
    
    def get_queryset(self):
        return Payment.objects.filter(booking__user=self.request.user)


class MyPaymentsView(LoginRequiredMixin, ListView):
    """View user's payment history."""
    model = Payment
    template_name = 'payments/my_payments.html'
    context_object_name = 'payments'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = Payment.objects.filter(booking__user=self.request.user)
        
        # Filter by status
        status = self.request.GET.get('status', 'all')
        if status != 'all':
            queryset = queryset.filter(status=status)
        
        # Filter by payment method
        method = self.request.GET.get('method', 'all')
        if method != 'all':
            queryset = queryset.filter(payment_method=method)
        
        # Filter by date range
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                queryset = queryset.filter(initiated_at__date__gte=date_from_obj)
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                queryset = queryset.filter(initiated_at__date__lte=date_to_obj)
            except ValueError:
                pass
        
        return queryset.select_related('booking').order_by('-initiated_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter values
        for param in ['status', 'method', 'date_from', 'date_to']:
            context[param] = self.request.GET.get(param, '')
        
        # Get payment statistics
        total_payments = Payment.objects.filter(booking__user=self.request.user).count()
        total_amount = Payment.objects.filter(
            booking__user=self.request.user,
            status='COMPLETED'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        context.update({
            'total_payments': total_payments,
            'total_amount': total_amount,
        })
        
        return context


@login_required
def wallet_view(request):
    """View and manage user wallet."""
    wallet, created = Wallet.objects.get_or_create(
        user=request.user,
        defaults={'balance': 0}
    )
    
    # Get wallet transactions
    transactions = wallet.transactions.all().order_by('-created_at')[:20]
    
    # Get payment methods
    payment_methods = Payment.PaymentMethod.choices
    
    return render(request, 'payments/wallet.html', {
        'wallet': wallet,
        'transactions': transactions,
        'payment_methods': payment_methods,
    })


@login_required
@require_http_methods(["POST"])
def add_wallet_credit(request):
    """Add credit to user wallet."""
    amount = request.POST.get('amount')
    payment_method = request.POST.get('payment_method')
    
    if not amount or not payment_method:
        messages.error(request, _('Amount and payment method are required.'))
        return redirect('payments:wallet')
    
    try:
        amount_decimal = Decimal(amount)
        if amount_decimal <= 0:
            raise ValueError("Amount must be positive")
        
        # Get or create wallet
        wallet, created = Wallet.objects.get_or_create(
            user=request.user,
            defaults={'balance': 0}
        )
        
        # Process payment (simulated)
        processor = PaymentProcessor()
        success, transaction_id, error = processor.process_payment(
            amount_decimal,
            payment_method,
            'Wallet Top-up',
            {'user_id': str(request.user.id), 'purpose': 'wallet_topup'}
        )
        
        if success:
            # Credit wallet
            wallet.credit(
                amount_decimal,
                source=f'{payment_method} Top-up',
                description=f'Wallet top-up via {payment_method}'
            )
            
            messages.success(request, _(f'Successfully added ${amount} to your wallet.'))
        else:
            messages.error(request, _(f'Payment failed: {error}'))
        
    except (ValueError, Exception) as e:
        messages.error(request, _(f'Error: {str(e)}'))
    
    return redirect('payments:wallet')


class RequestRefundView(LoginRequiredMixin, CreateView):
    """Request refund for a payment."""
    model = Refund
    form_class = RefundRequestForm
    template_name = 'payments/request_refund.html'
    success_url = reverse_lazy('payments:my_refunds')
    
    def get_initial(self):
        initial = super().get_initial()
        payment_id = self.kwargs.get('payment_id')
        
        if payment_id:
            try:
                payment = Payment.objects.get(
                    id=payment_id,
                    booking__user=self.request.user,
                    status='COMPLETED'
                )
                initial.update({
                    'payment': payment,
                    'amount': payment.amount,
                })
            except Payment.DoesNotExist:
                pass
        
        return initial
    
    def form_valid(self, form):
        payment = form.cleaned_data['payment']
        amount = form.cleaned_data['amount']
        reason = form.cleaned_data['reason']
        refund_method = form.cleaned_data['refund_method']
        
        # Validate refund amount
        if amount > payment.amount:
            form.add_error('amount', _('Refund amount cannot exceed payment amount.'))
            return self.form_invalid(form)
        
        # Check if payment is refundable
        if not payment.is_refundable:
            form.add_error(None, _('This payment is not refundable.'))
            return self.form_invalid(form)
        
        # Create refund
        try:
            refund = payment.initiate_refund(amount, reason)
            
            # Process refund (simulated)
            processor = PaymentProcessor()
            success, transaction_id, error = processor.process_refund(
                refund.amount,
                refund_method,
                f"Refund for {payment.payment_reference}"
            )
            
            if success:
                refund.external_refund_id = transaction_id
                refund.status = 'COMPLETED'
                refund.completed_at = timezone.now()
                refund.save()
                
                # If refunding to wallet, credit the amount
                if refund_method == 'WALLET':
                    wallet, created = Wallet.objects.get_or_create(
                        user=self.request.user,
                        defaults={'balance': 0}
                    )
                    wallet.credit(
                        amount,
                        source=f'Refund for {payment.payment_reference}',
                        description=reason
                    )
                
                messages.success(
                    self.request,
                    _(f'Refund initiated successfully. Refund Reference: {refund.refund_reference}')
                )
            else:
                messages.error(self.request, _(f'Refund failed: {error}'))
                return self.form_invalid(form)
            
        except Exception as e:
            messages.error(self.request, _(f'Error processing refund: {str(e)}'))
            return self.form_invalid(form)
        
        return super().form_valid(form)


class MyRefundsView(LoginRequiredMixin, ListView):
    """View user's refund history."""
    model = Refund
    template_name = 'payments/my_refunds.html'
    context_object_name = 'refunds'
    paginate_by = 10
    
    def get_queryset(self):
        return Refund.objects.filter(
            payment__booking__user=self.request.user
        ).select_related('payment', 'payment__booking').order_by('-requested_at')


class AdminPaymentListView(UserPassesTestMixin, ListView):
    """Payment list for admin dashboard."""
    model = Payment
    template_name = 'payments/admin/payment_list.html'
    context_object_name = 'payments'
    paginate_by = 50
    
    def test_func(self):
        return self.request.user.is_admin
    
    def get_queryset(self):
        queryset = Payment.objects.all().order_by('-initiated_at')
        
        # Filter by status
        status = self.request.GET.get('status', 'all')
        if status != 'all':
            queryset = queryset.filter(status=status)
        
        # Filter by payment method
        method = self.request.GET.get('method', 'all')
        if method != 'all':
            queryset = queryset.filter(payment_method=method)
        
        # Filter by date range
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                queryset = queryset.filter(initiated_at__date__gte=date_from_obj)
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                queryset = queryset.filter(initiated_at__date__lte=date_to_obj)
            except ValueError:
                pass
        
        # Search
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(payment_reference__icontains=search) |
                Q(external_payment_id__icontains=search) |
                Q(booking__booking_reference__icontains=search) |
                Q(booking__user__username__icontains=search) |
                Q(booking__user__email__icontains=search)
            )
        
        return queryset.select_related('booking', 'booking__user')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter values
        for param in ['status', 'method', 'date_from', 'date_to', 'search']:
            context[param] = self.request.GET.get(param, '')
        
        # Get payment statistics
        total_payments = Payment.objects.count()
        total_amount = Payment.objects.filter(
            status='COMPLETED'
        ).aggregate(total=Sum('amount'))['total'] or 0
        pending_payments = Payment.objects.filter(status='PENDING').count()
        
        context.update({
            'total_payments': total_payments,
            'total_amount': total_amount,
            'pending_payments': pending_payments,
        })
        
        return context


def payment_webhook(request):
    """Handle payment gateway webhooks."""
    if request.method == 'POST':
        try:
            # Parse webhook data
            data = json.loads(request.body)
            
            # Process webhook based on gateway
            processor = PaymentProcessor()
            success = processor.handle_webhook(data)
            
            if success:
                return JsonResponse({'status': 'success'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Webhook processing failed'})
            
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'})
    
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)


class PaymentInvoiceView(LoginRequiredMixin, DetailView):
    """Generate invoice for payment."""
    model = Payment
    template_name = 'payments/invoice.html'
    context_object_name = 'payment'
    
    def get_queryset(self):
        return Payment.objects.filter(booking__user=self.request.user)
"""
Views for Bookings operations.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, TemplateView, View
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import datetime, timedelta, date
import json

from .models import Booking, BookingHistory, BookingDocument
from .forms import BookingFilterForm, CancelBookingForm


class MyBookingsView(LoginRequiredMixin, ListView):
    """View user's bookings across all services."""
    model = Booking
    template_name = 'bookings/my_bookings.html'
    context_object_name = 'bookings'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = Booking.objects.filter(user=self.request.user)
        
        # Filter by status
        status = self.request.GET.get('status', 'all')
        if status != 'all':
            queryset = queryset.filter(status=status)
        
        # Filter by service type
        service_type = self.request.GET.get('service_type', 'all')
        if service_type != 'all':
            queryset = queryset.filter(service_type=service_type)
        
        # Filter by date range
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                queryset = queryset.filter(booking_date__date__gte=date_from_obj)
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                queryset = queryset.filter(booking_date__date__lte=date_to_obj)
            except ValueError:
                pass
        
        return queryset.select_related('user').order_by('-booking_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = BookingFilterForm(self.request.GET or None)
        
        # Add filter values to context
        for param in ['status', 'service_type', 'date_from', 'date_to']:
            context[param] = self.request.GET.get(param, '')
        
        # Get booking stats
        total_bookings = Booking.objects.filter(user=self.request.user).count()
        confirmed_bookings = Booking.objects.filter(
            user=self.request.user, 
            status='CONFIRMED'
        ).count()
        upcoming_bookings = Booking.objects.filter(
            user=self.request.user,
            status='CONFIRMED',
            check_in_date__gte=timezone.now().date()
        ).count()
        
        context.update({
            'total_bookings': total_bookings,
            'confirmed_bookings': confirmed_bookings,
            'upcoming_bookings': upcoming_bookings,
        })
        
        return context


class BookingDetailView(LoginRequiredMixin, DetailView):
    """View booking details."""
    model = Booking
    template_name = 'bookings/booking_detail.html'
    context_object_name = 'booking'
    
    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user).prefetch_related(
            'history', 'documents'
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        booking = self.object
        
        # Get service details
        context['service_details'] = booking.get_service_details()
        
        # Get booking history
        context['history'] = booking.history.all().order_by('-created_at')[:10]
        
        # Get documents
        context['documents'] = booking.documents.all()
        
        # Add cancel form if booking can be cancelled
        if booking.status in [Booking.Status.PENDING, Booking.Status.CONFIRMED]:
            context['cancel_form'] = CancelBookingForm(
                initial={'booking_id': str(booking.id)}
            )
        
        return context


@login_required
@require_http_methods(["POST"])
def cancel_booking_view(request, booking_id):
    """Cancel a booking."""
    booking = get_object_or_404(
        Booking, 
        id=booking_id, 
        user=request.user,
        status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED]
    )
    
    form = CancelBookingForm(request.POST)
    if form.is_valid():
        reason = form.cleaned_data['reason']
        
        # Calculate refund percentage based on cancellation policy
        refund_percentage = 0
        
        if booking.service_type == Booking.ServiceType.HOTEL:
            # Hotel cancellation policy
            if booking.check_in_date:
                days_before = (booking.check_in_date - timezone.now().date()).days
                if days_before >= 2:  # Free cancellation 2+ days before
                    refund_percentage = 100
                elif days_before >= 1:  # 50% refund 1 day before
                    refund_percentage = 50
        elif booking.service_type == Booking.ServiceType.CAR:
            # Car cancellation policy
            if booking.check_in_date:
                days_before = (booking.check_in_date - timezone.now().date()).days
                if days_before >= 7:  # Free cancellation 7+ days before
                    refund_percentage = 100
                elif days_before >= 3:  # 75% refund 3-6 days before
                    refund_percentage = 75
                elif days_before >= 1:  # 50% refund 1-2 days before
                    refund_percentage = 50
        elif booking.service_type == Booking.ServiceType.BUS:
            # Bus cancellation policy
            if booking.travel_date:
                hours_before = (booking.travel_date - timezone.now().date()).days * 24
                if hours_before >= 4:  # Free cancellation 4+ hours before
                    refund_percentage = 100
                else:
                    refund_percentage = 0  # No refund within 4 hours
        elif booking.service_type == Booking.ServiceType.TRAIN:
            # Train cancellation policy
            if booking.travel_date:
                days_before = (booking.travel_date - timezone.now().date()).days
                if days_before >= 2:  # Free cancellation 2+ days before
                    refund_percentage = 100
                elif days_before >= 1:  # 50% refund 1 day before
                    refund_percentage = 50
                else:
                    refund_percentage = 0  # No refund on same day
        
        # Cancel booking
        booking.cancel(reason, refund_percentage)
        
        # Create history entry
        BookingHistory.objects.create(
            booking=booking,
            old_status=booking.status,
            new_status=Booking.Status.CANCELLED,
            changed_by=request.user,
            notes=f"Cancelled by user. Refund: {refund_percentage}%",
            metadata={'refund_percentage': refund_percentage}
        )
        
        messages.success(
            request, 
            _(f'Booking cancelled successfully. Refund amount: ${booking.refund_amount:.2f}')
        )
    else:
        messages.error(request, _('Please provide a cancellation reason.'))
    
    return redirect('bookings:booking_detail', pk=booking_id)


@login_required
def download_ticket(request, booking_id):
    """Download booking ticket/invoice."""
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    # In production, generate PDF ticket
    # For now, return JSON with booking details
    ticket_data = {
        'booking_reference': booking.booking_reference,
        'service_type': booking.get_service_type_display(),
        'service_name': booking.service_name,
        'booking_date': booking.booking_date.strftime('%Y-%m-%d %H:%M'),
        'total_amount': float(booking.total_amount),
        'status': booking.get_status_display(),
        'contact_name': booking.contact_name,
        'contact_email': booking.contact_email,
        'contact_phone': booking.contact_phone,
        'service_details': booking.get_service_details(),
    }
    
    return JsonResponse(ticket_data)


class BookingCalendarView(LoginRequiredMixin, TemplateView):
    """View bookings on a calendar."""
    template_name = 'bookings/booking_calendar.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get bookings for the next 30 days
        start_date = timezone.now().date()
        end_date = start_date + timedelta(days=30)
        
        bookings = Booking.objects.filter(
            user=self.request.user,
            status='CONFIRMED'
        ).filter(
            Q(check_in_date__range=[start_date, end_date]) |
            Q(travel_date__range=[start_date, end_date])
        ).order_by('check_in_date', 'travel_date')
        
        # Format bookings for calendar
        calendar_bookings = []
        for booking in bookings:
            event_date = booking.check_in_date or booking.travel_date or booking.booking_date.date()
            calendar_bookings.append({
                'title': f"{booking.service_type}: {booking.service_name}",
                'start': event_date.isoformat(),
                'end': (booking.check_out_date or event_date).isoformat(),
                'color': self.get_service_color(booking.service_type),
                'url': reverse_lazy('bookings:booking_detail', kwargs={'pk': booking.id}),
                'extendedProps': {
                    'booking_ref': booking.booking_reference,
                    'status': booking.get_status_display(),
                }
            })
        
        context['bookings_json'] = json.dumps(calendar_bookings)
        return context
    
    def get_service_color(self, service_type):
        """Get color for service type in calendar."""
        colors = {
            'HOTEL': '#3498db',  # Blue
            'CAR': '#2ecc71',    # Green
            'BUS': '#e74c3c',    # Red
            'TRAIN': '#f39c12',  # Orange
        }
        return colors.get(service_type, '#95a5a6')


def booking_stats_api(request):
    """API endpoint for booking statistics."""
    if request.method == 'GET' and request.user.is_authenticated:
        # Get time range
        days = int(request.GET.get('days', 30))
        start_date = timezone.now().date() - timedelta(days=days)
        
        # Get booking counts by service type
        bookings = Booking.objects.filter(
            user=request.user,
            booking_date__date__gte=start_date
        )
        
        stats = {
            'total_bookings': bookings.count(),
            'total_spent': float(bookings.aggregate(total=Sum('total_amount'))['total'] or 0),
            'by_service': list(bookings.values('service_type').annotate(
                count=Count('id'),
                amount=Sum('total_amount')
            ).order_by('-count')),
            'by_status': list(bookings.values('status').annotate(
                count=Count('id')
            ).order_by('status')),
        }
        
        return JsonResponse({'success': True, 'stats': stats})
    
    return JsonResponse({'success': False, 'error': 'Unauthorized'})


class AdminBookingListView(UserPassesTestMixin, ListView):
    """Booking list for admin dashboard."""
    model = Booking
    template_name = 'bookings/admin/booking_list.html'
    context_object_name = 'bookings'
    paginate_by = 50
    
    def test_func(self):
        return self.request.user.is_admin
    
    def get_queryset(self):
        queryset = Booking.objects.all().order_by('-booking_date')
        
        # Filter by status
        status = self.request.GET.get('status', 'all')
        if status != 'all':
            queryset = queryset.filter(status=status)
        
        # Filter by service type
        service_type = self.request.GET.get('service_type', 'all')
        if service_type != 'all':
            queryset = queryset.filter(service_type=service_type)
        
        # Filter by date range
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                queryset = queryset.filter(booking_date__date__gte=date_from_obj)
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                queryset = queryset.filter(booking_date__date__lte=date_to_obj)
            except ValueError:
                pass
        
        # Search
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(booking_reference__icontains=search) |
                Q(user__username__icontains=search) |
                Q(user__email__icontains=search) |
                Q(contact_name__icontains=search) |
                Q(contact_email__icontains=search)
            )
        
        return queryset.select_related('user')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter values
        for param in ['status', 'service_type', 'date_from', 'date_to', 'search']:
            context[param] = self.request.GET.get(param, '')
        
        # Get summary statistics
        total_bookings = Booking.objects.count()
        total_revenue = Booking.objects.filter(
            status__in=['CONFIRMED', 'COMPLETED']
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        context.update({
            'total_bookings': total_bookings,
            'total_revenue': total_revenue,
        })
        
        return context


@method_decorator(login_required, name='dispatch')
class BookingInvoiceView(DetailView):
    """Generate invoice for booking."""
    model = Booking
    template_name = 'bookings/invoice.html'
    context_object_name = 'booking'
    
    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user)
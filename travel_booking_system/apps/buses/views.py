"""
Views for Bus operations.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, TemplateView, View
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import datetime, timedelta, date
import json

from .models import Bus, BusOperator, BusType, BusBooking, BusReview, BusStop
from .seat_manager import SeatManager, SeatPricingManager, SeatAutoAllocator
from .forms import BusSearchForm, BusBookingForm, BusReviewForm


class BusSearchView(ListView):
    """Search and list buses."""
    model = Bus
    template_name = 'buses/bus_search.html'
    context_object_name = 'buses'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = Bus.objects.filter(status='ACTIVE').select_related(
            'operator', 'bus_type'
        )
        
        # Get search parameters
        route_from = self.request.GET.get('from', '')
        route_to = self.request.GET.get('to', '')
        travel_date = self.request.GET.get('travel_date')
        bus_type = self.request.GET.get('bus_type')
        sort_by = self.request.GET.get('sort_by', 'departure')
        
        # Apply filters
        if route_from:
            queryset = queryset.filter(route_from__icontains=route_from)
        
        if route_to:
            queryset = queryset.filter(route_to__icontains=route_to)
        
        if bus_type:
            queryset = queryset.filter(bus_type_id=bus_type)
        
        if travel_date:
            try:
                travel_date_obj = datetime.strptime(travel_date, '%Y-%m-%d').date()
                # Filter buses that run on this date
                # For now, we'll just return all active buses
                # In production, check schedule
                pass
            except ValueError:
                pass
        
        # Apply sorting
        sort_options = {
            'departure': 'departure_time',
            'arrival': 'arrival_time',
            'duration': 'duration_hours',
            'price_low': 'base_fare',
            'price_high': '-base_fare',
            'rating': '-operator__rating',
        }
        sort_field = sort_options.get(sort_by, 'departure_time')
        queryset = queryset.order_by(sort_field)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = BusSearchForm(self.request.GET or None)
        context['bus_types'] = BusType.objects.all()
        context['operators'] = BusOperator.objects.all()
        
        # Add search parameters to context
        for param in ['from', 'to', 'travel_date', 'bus_type', 'sort_by']:
            context[param] = self.request.GET.get(param, '')
        
        return context


class BusDetailView(DetailView):
    """Bus details and seat selection."""
    model = Bus
    template_name = 'buses/bus_detail.html'
    context_object_name = 'bus'
    
    def get_queryset(self):
        return Bus.objects.filter(status='ACTIVE').select_related(
            'operator', 'bus_type'
        ).prefetch_related('stops', 'seats', 'reviews')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        bus = self.object
        
        # Get travel date from query params or default to tomorrow
        travel_date = self.request.GET.get('travel_date')
        if not travel_date:
            travel_date = (timezone.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Get seat layout
        seat_layout = SeatManager.get_seat_layout(str(bus.id))
        
        # Get available seats for the date
        try:
            travel_date_obj = datetime.strptime(travel_date, '%Y-%m-%d').date()
            available_seats = SeatManager.get_available_seats_for_date(
                str(bus.id), travel_date_obj
            )
            seat_layout['available_seats_for_date'] = available_seats
        except ValueError:
            available_seats = []
        
        # Get reviews
        reviews = bus.reviews.all().order_by('-created_at')[:5]
        
        # Get booking form
        context['booking_form'] = BusBookingForm(
            initial={
                'bus_id': str(bus.id),
                'travel_date': travel_date,
            }
        )
        
        context.update({
            'seat_layout': json.dumps(seat_layout),
            'available_seats': available_seats,
            'travel_date': travel_date,
            'reviews': reviews,
            'review_form': BusReviewForm() if self.request.user.is_authenticated else None,
            'stops': bus.stops.all().order_by('sequence'),
        })
        
        return context


@method_decorator(login_required, name='dispatch')
class BusBookingView(CreateView):
    """Handle bus booking."""
    form_class = BusBookingForm
    template_name = 'buses/bus_booking.html'
    
    def form_valid(self, form):
        # Get cleaned data
        bus_id = form.cleaned_data['bus_id']
        travel_date = form.cleaned_data['travel_date']
        seats = form.cleaned_data['seats']
        passenger_name = form.cleaned_data['passenger_name']
        passenger_age = form.cleaned_data['passenger_age']
        passenger_gender = form.cleaned_data['passenger_gender']
        passenger_phone = form.cleaned_data['passenger_phone']
        passenger_email = form.cleaned_data['passenger_email']
        boarding_point = form.cleaned_data['boarding_point']
        dropping_point = form.cleaned_data['dropping_point']
        special_requests = form.cleaned_data['special_requests']
        
        # Get bus
        bus = get_object_or_404(Bus, id=bus_id, status='ACTIVE')
        
        # Validate seat selection
        is_valid, error = SeatManager.validate_seat_selection(
            bus_id, seats, passenger_gender
        )
        
        if not is_valid:
            messages.error(self.request, error)
            return self.form_invalid(form)
        
        # Book seats
        success, booked_seats, total_amount, error = SeatManager.book_seats(
            bus_id, seats, travel_date, self.request.user.id
        )
        
        if not success:
            messages.error(self.request, error)
            return self.form_invalid(form)
        
        # Create booking
        booking = BusBooking.objects.create(
            user=self.request.user,
            bus=bus,
            travel_date=travel_date,
            seats_booked=booked_seats,
            total_passengers=len(booked_seats),
            total_amount=total_amount,
            passenger_name=passenger_name,
            passenger_age=passenger_age,
            passenger_gender=passenger_gender,
            passenger_phone=passenger_phone,
            passenger_email=passenger_email,
            boarding_point=boarding_point,
            dropping_point=dropping_point,
            status=BusBooking.BookingStatus.PENDING,
        )
        
        messages.success(
            self.request,
            _('Bus seats booked successfully! Please proceed to payment.')
        )
        
        # Store booking data in session for payment
        self.request.session['pending_booking'] = {
            'booking_id': str(booking.id),
            'service_type': 'BUS',
            'amount': str(total_amount),
            'details': {
                'bus_number': bus.bus_number,
                'route': bus.route_name,
                'travel_date': travel_date,
                'seats': booked_seats,
                'passenger_name': passenger_name,
                'total_amount': total_amount,
                'boarding_point': boarding_point,
                'dropping_point': dropping_point,
                'departure_time': bus.departure_time.strftime('%H:%M'),
                'arrival_time': bus.arrival_time.strftime('%H:%M'),
            }
        }
        
        return redirect('payments:create_payment')
    
    def form_invalid(self, form):
        messages.error(self.request, _('Please correct the errors below.'))
        return super().form_invalid(form)


class SeatSelectionView(TemplateView):
    """Seat selection interface."""
    template_name = 'buses/seat_selection.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        bus_id = self.request.GET.get('bus_id')
        travel_date = self.request.GET.get('travel_date')
        
        if bus_id:
            bus = get_object_or_404(Bus, id=bus_id, status='ACTIVE')
            seat_layout = SeatManager.get_seat_layout(bus_id)
            
            context.update({
                'bus': bus,
                'travel_date': travel_date,
                'seat_layout': json.dumps(seat_layout),
                'max_seats': 6,  # Maximum seats per booking
            })
        
        return context


@login_required
@require_http_methods(["POST"])
def submit_bus_review(request, bus_id):
    """Submit a bus review."""
    bus = get_object_or_404(Bus, id=bus_id, status='ACTIVE')
    
    # Check if user has already reviewed
    existing_review = BusReview.objects.filter(
        bus=bus, 
        user=request.user
    ).first()
    
    if existing_review:
        messages.error(request, _('You have already reviewed this bus.'))
        return redirect('buses:bus_detail', pk=bus_id)
    
    form = BusReviewForm(request.POST)
    if form.is_valid():
        review = form.save(commit=False)
        review.bus = bus
        review.user = request.user
        review.save()
        
        messages.success(request, _('Thank you for your review!'))
    else:
        messages.error(request, _('Please correct the errors in your review.'))
    
    return redirect('buses:bus_detail', pk=bus_id)


def bus_availability_api(request):
    """API endpoint to check bus availability."""
    if request.method == 'GET':
        bus_id = request.GET.get('bus_id')
        travel_date = request.GET.get('travel_date')
        
        if not all([bus_id, travel_date]):
            return JsonResponse({
                'success': False,
                'error': 'Missing required parameters'
            })
        
        try:
            bus = Bus.objects.get(id=bus_id, status='ACTIVE')
            travel_date_obj = datetime.strptime(travel_date, '%Y-%m-%d').date()
            
            # Get available seats
            available_seats = SeatManager.get_available_seats_for_date(
                bus_id, travel_date_obj
            )
            
            # Calculate dynamic fares
            seat_fares = {}
            if available_seats:
                # Sample fare calculation for first 5 seats
                sample_seats = available_seats[:5]
                seat_fares = SeatPricingManager.calculate_dynamic_fare(
                    bus_id, sample_seats, travel_date_obj
                )
            
            return JsonResponse({
                'success': True,
                'bus': {
                    'id': str(bus.id),
                    'bus_number': bus.bus_number,
                    'operator': bus.operator.name,
                    'bus_type': bus.bus_type.name,
                    'route': bus.route_name,
                    'departure_time': bus.departure_time.strftime('%H:%M'),
                    'arrival_time': bus.arrival_time.strftime('%H:%M'),
                    'duration': float(bus.duration_hours) if bus.duration_hours else None,
                    'base_fare': float(bus.base_fare),
                    'final_fare': float(bus.final_fare),
                },
                'availability': {
                    'total_seats': bus.total_seats,
                    'available_seats': len(available_seats),
                    'available_seat_numbers': available_seats,
                    'is_full': len(available_seats) == 0,
                },
                'sample_fares': seat_fares,
            })
            
        except Bus.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Bus not found'})
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Invalid date format'})
    
    return JsonResponse({'success': False, 'error': 'Invalid method'})


def auto_allocate_seats_api(request):
    """API endpoint for automatic seat allocation."""
    if request.method == 'GET':
        bus_id = request.GET.get('bus_id')
        num_seats = int(request.GET.get('num_seats', 1))
        preferences = request.GET.get('preferences', '{}')
        
        if not bus_id or num_seats < 1:
            return JsonResponse({
                'success': False,
                'error': 'Invalid parameters'
            })
        
        try:
            # Parse preferences
            pref_dict = json.loads(preferences)
            
            # Allocate seats
            allocated_seats = SeatAutoAllocator.allocate_seats(
                bus_id, num_seats, pref_dict
            )
            
            return JsonResponse({
                'success': True,
                'allocated_seats': allocated_seats,
                'num_seats_allocated': len(allocated_seats),
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid preferences format'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid method'})


class MyBusBookingsView(LoginRequiredMixin, ListView):
    """View user's bus bookings."""
    model = BusBooking
    template_name = 'buses/my_bookings.html'
    context_object_name = 'bookings'
    paginate_by = 10
    
    def get_queryset(self):
        return BusBooking.objects.filter(
            user=self.request.user
        ).select_related('bus', 'bus__operator').order_by('-created_at')


@login_required
@require_http_methods(["POST"])
def cancel_bus_booking(request, booking_id):
    """Cancel a bus booking."""
    booking = get_object_or_404(
        BusBooking, 
        id=booking_id, 
        user=request.user,
        status__in=['PENDING', 'CONFIRMED']
    )
    
    reason = request.POST.get('reason', '')
    booking.cancel_booking(reason)
    
    messages.success(request, _('Booking cancelled successfully.'))
    return redirect('buses:my_bookings')


class AdminBusListView(UserPassesTestMixin, ListView):
    """Bus list for admin dashboard."""
    model = Bus
    template_name = 'buses/admin/bus_list.html'
    context_object_name = 'buses'
    paginate_by = 20
    
    def test_func(self):
        return self.request.user.is_admin
    
    def get_queryset(self):
        queryset = Bus.objects.all().order_by('-created_at')
        
        # Filter by status
        status = self.request.GET.get('status', 'all')
        if status != 'all':
            queryset = queryset.filter(status=status)
        
        # Filter by route
        route_from = self.request.GET.get('from', '')
        if route_from:
            queryset = queryset.filter(route_from__icontains=route_from)
        
        route_to = self.request.GET.get('to', '')
        if route_to:
            queryset = queryset.filter(route_to__icontains=route_to)
        
        # Search
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(bus_number__icontains=search) |
                Q(operator__name__icontains=search)
            )
        
        return queryset.select_related('operator', 'bus_type')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_filter'] = self.request.GET.get('status', 'all')
        context['from_filter'] = self.request.GET.get('from', '')
        context['to_filter'] = self.request.GET.get('to', '')
        context['search_query'] = self.request.GET.get('search', '')
        return context


def bus_routes_api(request):
    """API endpoint to get popular bus routes."""
    if request.method == 'GET':
        # Get popular routes (most bookings)
        from .models import BusBooking
        
        popular_routes = Bus.objects.filter(
            status='ACTIVE',
            bookings__isnull=False
        ).annotate(
            booking_count=models.Count('bookings')
        ).order_by('-booking_count')[:10]
        
        routes_data = []
        for bus in popular_routes:
            routes_data.append({
                'from': bus.route_from,
                'to': bus.route_to,
                'bus_count': Bus.objects.filter(
                    route_from=bus.route_from,
                    route_to=bus.route_to,
                    status='ACTIVE'
                ).count(),
                'min_fare': float(Bus.objects.filter(
                    route_from=bus.route_from,
                    route_to=bus.route_to
                ).order_by('base_fare').first().base_fare),
            })
        
        return JsonResponse({
            'success': True,
            'routes': routes_data
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid method'})
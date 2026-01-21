"""
Views for Train operations.
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

from .models import Train, CoachType, TrainBooking, TrainReview, TrainStop, FareRule
from .seat_manager import TrainSeatManager, TrainAvailabilityManager
from .forms import TrainSearchForm, TrainBookingForm, TrainReviewForm


class TrainSearchView(ListView):
    """Search and list trains."""
    model = Train
    template_name = 'trains/train_search.html'
    context_object_name = 'trains'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = Train.objects.filter(status='ACTIVE')
        
        # Get search parameters
        from_station = self.request.GET.get('from', '')
        to_station = self.request.GET.get('to', '')
        travel_date = self.request.GET.get('travel_date')
        train_type = self.request.GET.get('train_type')
        sort_by = self.request.GET.get('sort_by', 'departure')
        
        # Apply filters
        if from_station:
            queryset = queryset.filter(source_station__icontains=from_station)
        
        if to_station:
            queryset = queryset.filter(destination_station__icontains=to_station)
        
        if train_type:
            queryset = queryset.filter(train_type=train_type)
        
        # Apply sorting
        sort_options = {
            'departure': 'departure_time',
            'arrival': 'arrival_time',
            'duration': 'duration_hours',
            'train_number': 'train_number',
        }
        sort_field = sort_options.get(sort_by, 'departure_time')
        queryset = queryset.order_by(sort_field)
        
        return queryset.select_related().prefetch_related('stops')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = TrainSearchForm(self.request.GET or None)
        context['coach_types'] = CoachType.objects.all()
        context['train_types'] = Train.TrainType.choices
        
        # Add search parameters to context
        for param in ['from', 'to', 'travel_date', 'train_type', 'sort_by']:
            context[param] = self.request.GET.get(param, '')
        
        return context


class TrainDetailView(DetailView):
    """Train details, schedule, and booking."""
    model = Train
    template_name = 'trains/train_detail.html'
    context_object_name = 'train'
    
    def get_queryset(self):
        return Train.objects.filter(status='ACTIVE').prefetch_related(
            'stops', 'coaches', 'reviews'
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        train = self.object
        
        # Get travel date from query params or default to tomorrow
        travel_date = self.request.GET.get('travel_date')
        if not travel_date:
            travel_date = (timezone.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Get stops
        stops = train.stops.all().order_by('sequence')
        
        # Get coach types available
        coach_types = CoachType.objects.filter(
            coaches__train=train
        ).distinct()
        
        # Get availability prediction
        if self.request.GET.get('from') and self.request.GET.get('to'):
            from_station = self.request.GET.get('from')
            to_station = self.request.GET.get('to')
            
            # Find stops
            from_stop = stops.filter(station_name__icontains=from_station).first()
            to_stop = stops.filter(station_name__icontains=to_station).first()
            
            if from_stop and to_stop and from_stop.sequence < to_stop.sequence:
                try:
                    travel_date_obj = datetime.strptime(travel_date, '%Y-%m-%d').date()
                    prediction = TrainAvailabilityManager.get_availability_prediction(
                        str(train.id),
                        str(coach_types.first().id) if coach_types.exists() else None,
                        str(from_stop.id),
                        str(to_stop.id),
                        travel_date_obj
                    )
                    context['availability_prediction'] = prediction
                    
                    # Get alternative trains
                    alternatives = TrainAvailabilityManager.get_alternative_trains(
                        from_station, to_station, travel_date_obj
                    )
                    context['alternative_trains'] = alternatives
                    
                except ValueError:
                    pass
        
        # Get reviews
        reviews = train.reviews.all().order_by('-created_at')[:5]
        
        # Get booking form
        context['booking_form'] = TrainBookingForm(
            initial={
                'train_id': str(train.id),
                'travel_date': travel_date,
            }
        )
        
        context.update({
            'stops': stops,
            'coach_types': coach_types,
            'travel_date': travel_date,
            'reviews': reviews,
            'review_form': TrainReviewForm() if self.request.user.is_authenticated else None,
        })
        
        return context


@method_decorator(login_required, name='dispatch')
class TrainBookingView(CreateView):
    """Handle train booking."""
    form_class = TrainBookingForm
    template_name = 'trains/train_booking.html'
    
    def form_valid(self, form):
        # Get cleaned data
        train_id = form.cleaned_data['train_id']
        from_station = form.cleaned_data['from_station']
        to_station = form.cleaned_data['to_station']
        travel_date = form.cleaned_data['travel_date']
        coach_type_id = form.cleaned_data['coach_type']
        quota = form.cleaned_data['quota']
        seats = form.cleaned_data['seats']
        passenger_name = form.cleaned_data['passenger_name']
        passenger_age = form.cleaned_data['passenger_age']
        passenger_gender = form.cleaned_data['passenger_gender']
        passenger_id_type = form.cleaned_data['passenger_id_type']
        passenger_id_number = form.cleaned_data['passenger_id_number']
        passenger_phone = form.cleaned_data['passenger_phone']
        passenger_email = form.cleaned_data['passenger_email']
        
        # Get train
        train = get_object_or_404(Train, id=train_id, status='ACTIVE')
        
        # Find stops
        from_stop = get_object_or_404(
            TrainStop, 
            train=train, 
            station_name__icontains=from_station
        )
        to_stop = get_object_or_404(
            TrainStop, 
            train=train, 
            station_name__icontains=to_station
        )
        
        if from_stop.sequence >= to_stop.sequence:
            messages.error(self.request, _('Destination must be after departure station.'))
            return self.form_invalid(form)
        
        # Book seats
        success, booking_data, error = TrainSeatManager.book_seats(
            train_id,
            coach_type_id,
            str(from_stop.id),
            str(to_stop.id),
            travel_date,
            seats.split(','),
            quota
        )
        
        if not success:
            # Check for RAC/Waitlist
            status, position, message = TrainSeatManager.check_rac_or_waitlist(
                train_id,
                coach_type_id,
                str(from_stop.id),
                str(to_stop.id),
                travel_date,
                len(seats.split(',')),
                quota
            )
            
            if status in ['RAC', 'WAITLIST']:
                # Allow booking with RAC/Waitlist status
                fare_details = TrainSeatManager.calculate_journey_fare(
                    train_id, coach_type_id, str(from_stop.id), str(to_stop.id), quota
                )
                
                booking_data = {
                    'train_number': train.train_number,
                    'train_name': train.train_name,
                    'from_station': from_stop.station_name,
                    'to_station': to_stop.station_name,
                    'travel_date': travel_date,
                    'coach_type': CoachType.objects.get(id=coach_type_id).name,
                    'seats': seats.split(','),
                    'quota': quota,
                    'status': status,
                    'position': position,
                    'fare_details': fare_details,
                    'total_amount': fare_details['total_amount'],
                }
                
                messages.warning(self.request, f"Booking confirmed with {status} status. Position: {position}")
                success = True
            else:
                messages.error(self.request, f"Booking failed: {error}")
                return self.form_invalid(form)
        
        if success:
            # Create booking
            booking = TrainBooking.objects.create(
                user=self.request.user,
                train=train,
                from_station=from_stop,
                to_station=to_stop,
                travel_date=travel_date,
                coach_type_id=coach_type_id,
                seats_booked=booking_data['seats'],
                total_passengers=len(booking_data['seats']),
                quota=quota,
                status=booking_data.get('status', 'CONFIRMED'),
                base_fare=booking_data['fare_details']['base_fare'],
                reservation_charge=booking_data['fare_details']['reservation_charge'],
                superfast_charge=booking_data['fare_details']['superfast_charge'],
                tatkal_charge=booking_data['fare_details']['tatkal_charge'],
                service_tax=booking_data['fare_details']['service_tax'],
                total_amount=booking_data['total_amount'],
                passenger_name=passenger_name,
                passenger_age=passenger_age,
                passenger_gender=passenger_gender,
                passenger_id_type=passenger_id_type,
                passenger_id_number=passenger_id_number,
                passenger_phone=passenger_phone,
                passenger_email=passenger_email,
            )
            
            if booking_data.get('status') in ['RAC', 'WAITLIST']:
                messages.success(
                    self.request,
                    _(f'Train booking confirmed with {booking_data["status"]} status. PNR: {booking.pnr_number}')
                )
            else:
                messages.success(
                    self.request,
                    _(f'Train booking confirmed successfully! PNR: {booking.pnr_number}')
                )
            
            # Store booking data in session for payment
            self.request.session['pending_booking'] = {
                'booking_id': str(booking.id),
                'service_type': 'TRAIN',
                'amount': str(booking.total_amount),
                'details': {
                    'train_number': train.train_number,
                    'train_name': train.train_name,
                    'from_station': from_stop.station_name,
                    'to_station': to_stop.station_name,
                    'travel_date': travel_date,
                    'coach_type': CoachType.objects.get(id=coach_type_id).name,
                    'seats': booking_data['seats'],
                    'quota': quota,
                    'pnr_number': booking.pnr_number,
                    'total_amount': booking.total_amount,
                    'status': booking_data.get('status', 'CONFIRMED'),
                }
            }
            
            return redirect('payments:create_payment')
        
        return self.form_invalid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, _('Please correct the errors below.'))
        return super().form_invalid(form)


@login_required
@require_http_methods(["POST"])
def submit_train_review(request, train_id):
    """Submit a train review."""
    train = get_object_or_404(Train, id=train_id, status='ACTIVE')
    
    # Check if user has already reviewed
    existing_review = TrainReview.objects.filter(
        train=train, 
        user=request.user
    ).first()
    
    if existing_review:
        messages.error(request, _('You have already reviewed this train.'))
        return redirect('trains:train_detail', pk=train_id)
    
    form = TrainReviewForm(request.POST)
    if form.is_valid():
        review = form.save(commit=False)
        review.train = train
        review.user = request.user
        review.save()
        
        messages.success(request, _('Thank you for your review!'))
    else:
        messages.error(request, _('Please correct the errors in your review.'))
    
    return redirect('trains:train_detail', pk=train_id)


def train_availability_api(request):
    """API endpoint to check train availability."""
    if request.method == 'GET':
        train_id = request.GET.get('train_id')
        from_station = request.GET.get('from')
        to_station = request.GET.get('to')
        travel_date = request.GET.get('travel_date')
        coach_type_id = request.GET.get('coach_type')
        
        if not all([train_id, from_station, to_station, travel_date]):
            return JsonResponse({
                'success': False,
                'error': 'Missing required parameters'
            })
        
        try:
            train = Train.objects.get(id=train_id, status='ACTIVE')
            travel_date_obj = datetime.strptime(travel_date, '%Y-%m-%d').date()
            
            # Find stops
            from_stop = train.stops.filter(station_name__icontains=from_station).first()
            to_stop = train.stops.filter(station_name__icontains=to_station).first()
            
            if not from_stop or not to_stop:
                return JsonResponse({
                    'success': False,
                    'error': 'Stations not found on this train route'
                })
            
            if from_stop.sequence >= to_stop.sequence:
                return JsonResponse({
                    'success': False,
                    'error': 'Destination must be after departure station'
                })
            
            # Get coach types if not specified
            if not coach_type_id:
                coach_types = CoachType.objects.filter(coaches__train=train).distinct()
                coach_type_id = str(coach_types.first().id) if coach_types.exists() else None
            
            # Check availability
            if coach_type_id:
                # Get available seats
                from .models import Coach
                coach = Coach.objects.filter(
                    train=train,
                    coach_type_id=coach_type_id,
                    status='AVAILABLE'
                ).first()
                
                if coach:
                    available_seats = TrainSeatManager.get_available_seats_for_journey(
                        coach.id,
                        from_stop.sequence,
                        to_stop.sequence,
                        travel_date_obj,
                        'GENERAL'
                    )
                    
                    # Calculate fare
                    fare_details = TrainSeatManager.calculate_journey_fare(
                        train_id,
                        coach_type_id,
                        str(from_stop.id),
                        str(to_stop.id),
                        'GENERAL'
                    )
                    
                    # Check RAC/Waitlist status
                    status, position, message = TrainSeatManager.check_rac_or_waitlist(
                        train_id,
                        coach_type_id,
                        str(from_stop.id),
                        str(to_stop.id),
                        travel_date_obj,
                        1,  # Check for 1 passenger
                        'GENERAL'
                    )
                    
                    return JsonResponse({
                        'success': True,
                        'train': {
                            'number': train.train_number,
                            'name': train.train_name,
                            'type': train.train_type,
                        },
                        'journey': {
                            'from': from_stop.station_name,
                            'to': to_stop.station_name,
                            'distance_km': to_stop.distance_from_source - from_stop.distance_from_source,
                        },
                        'availability': {
                            'status': status,
                            'position': position,
                            'available_seats': len(available_seats),
                            'available_seat_numbers': available_seats[:10],  # First 10 seats
                        },
                        'fare': fare_details,
                        'message': message,
                    })
            
            return JsonResponse({
                'success': True,
                'train': {
                    'number': train.train_number,
                    'name': train.train_name,
                },
                'availability': {
                    'status': 'NOT_AVAILABLE',
                    'position': 0,
                    'available_seats': 0,
                },
                'message': 'No coaches available',
            })
            
        except Train.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Train not found'})
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Invalid date format'})
    
    return JsonResponse({'success': False, 'error': 'Invalid method'})


class MyTrainBookingsView(LoginRequiredMixin, ListView):
    """View user's train bookings."""
    model = TrainBooking
    template_name = 'trains/my_bookings.html'
    context_object_name = 'bookings'
    paginate_by = 10
    
    def get_queryset(self):
        return TrainBooking.objects.filter(
            user=self.request.user
        ).select_related('train', 'coach_type', 'from_station', 'to_station').order_by('-booked_at')


@login_required
def train_booking_detail(request, pnr_number):
    """View train booking details by PNR."""
    booking = get_object_or_404(
        TrainBooking, 
        pnr_number=pnr_number,
        user=request.user
    )
    
    return render(request, 'trains/booking_detail.html', {
        'booking': booking
    })


@login_required
@require_http_methods(["POST"])
def cancel_train_booking(request, booking_id):
    """Cancel a train booking."""
    booking = get_object_or_404(
        TrainBooking, 
        id=booking_id, 
        user=request.user,
        status__in=['PENDING', 'CONFIRMED', 'RAC']
    )
    
    # Calculate cancellation charge based on time before departure
    travel_datetime = datetime.combine(booking.travel_date, booking.train.departure_time)
    time_before = travel_datetime - timezone.now()
    hours_before = time_before.total_seconds() / 3600
    
    # Simplified cancellation rules
    if hours_before > 48:
        cancellation_charge = booking.base_fare * Decimal('0.25')  # 25%
    elif hours_before > 24:
        cancellation_charge = booking.base_fare * Decimal('0.50')  # 50%
    else:
        cancellation_charge = booking.base_fare * Decimal('0.75')  # 75%
    
    # Update booking
    booking.status = 'CANCELLED'
    booking.cancellation_charge = cancellation_charge
    booking.cancellation_time = timezone.now()
    booking.cancellation_reason = request.POST.get('reason', '')
    booking.save()
    
    # Release seats (in production, you'd update seat availability)
    
    messages.success(
        request, 
        _(f'Booking cancelled. Cancellation charge: ${cancellation_charge:.2f}')
    )
    return redirect('trains:my_bookings')


class AdminTrainListView(UserPassesTestMixin, ListView):
    """Train list for admin dashboard."""
    model = Train
    template_name = 'trains/admin/train_list.html'
    context_object_name = 'trains'
    paginate_by = 20
    
    def test_func(self):
        return self.request.user.is_admin
    
    def get_queryset(self):
        queryset = Train.objects.all().order_by('-created_at')
        
        # Filter by status
        status = self.request.GET.get('status', 'all')
        if status != 'all':
            queryset = queryset.filter(status=status)
        
        # Filter by train type
        train_type = self.request.GET.get('train_type', '')
        if train_type:
            queryset = queryset.filter(train_type=train_type)
        
        # Search
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(train_number__icontains=search) |
                Q(train_name__icontains=search) |
                Q(source_station__icontains=search) |
                Q(destination_station__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_filter'] = self.request.GET.get('status', 'all')
        context['train_type_filter'] = self.request.GET.get('train_type', '')
        context['search_query'] = self.request.GET.get('search', '')
        return context


def train_schedule_api(request):
    """API endpoint to get train schedule."""
    if request.method == 'GET':
        train_number = request.GET.get('train_number')
        
        if not train_number:
            return JsonResponse({
                'success': False,
                'error': 'Train number required'
            })
        
        try:
            train = Train.objects.get(train_number=train_number, status='ACTIVE')
            stops = train.stops.all().order_by('sequence')
            
            schedule = []
            for stop in stops:
                schedule.append({
                    'station_name': stop.station_name,
                    'station_code': stop.station_code,
                    'arrival_time': stop.arrival_time.strftime('%H:%M') if stop.arrival_time else None,
                    'departure_time': stop.departure_time.strftime('%H:%M') if stop.departure_time else None,
                    'halt_minutes': stop.halt_minutes,
                    'distance_km': stop.distance_from_source,
                    'day_number': stop.day_number,
                })
            
            return JsonResponse({
                'success': True,
                'train': {
                    'number': train.train_number,
                    'name': train.train_name,
                    'type': train.train_type,
                    'source': train.source_station,
                    'destination': train.destination_station,
                    'departure_time': train.departure_time.strftime('%H:%M'),
                    'arrival_time': train.arrival_time.strftime('%H:%M'),
                    'distance_km': train.distance_km,
                },
                'schedule': schedule,
            })
            
        except Train.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Train not found'})
    
    return JsonResponse({'success': False, 'error': 'Invalid method'})
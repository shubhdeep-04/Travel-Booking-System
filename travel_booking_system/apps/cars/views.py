"""
Views for Car operations.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, TemplateView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from datetime import datetime, timedelta

from .models import Car, CarCategory, CarBrand, CarReview
from .forms import CarSearchForm, CarBookingForm, CarReviewForm


class CarListView(ListView):
    """List all available cars with filters."""
    model = Car
    template_name = 'cars/car_list.html'
    context_object_name = 'cars'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Car.objects.filter(
            is_active=True,
            status='AVAILABLE'
        ).select_related('brand', 'category')
        
        # Get filter parameters
        city = self.request.GET.get('city', '')
        category = self.request.GET.get('category')
        transmission = self.request.GET.get('transmission')
        fuel_type = self.request.GET.get('fuel_type')
        min_price = self.request.GET.get('min_price')
        max_price = self.request.GET.get('max_price')
        sort_by = self.request.GET.get('sort_by', 'price_low')
        
        # Apply filters
        if city:
            queryset = queryset.filter(city__icontains=city)
        
        if category:
            queryset = queryset.filter(category_id=category)
        
        if transmission:
            queryset = queryset.filter(transmission=transmission)
        
        if fuel_type:
            queryset = queryset.filter(fuel_type=fuel_type)
        
        if min_price:
            queryset = queryset.filter(daily_rate__gte=min_price)
        
        if max_price:
            queryset = queryset.filter(daily_rate__lte=max_price)
        
        # Apply sorting
        sort_options = {
            'price_low': 'daily_rate',
            'price_high': '-daily_rate',
            'newest': '-created_at',
            'brand': 'brand__name',
        }
        sort_field = sort_options.get(sort_by, 'daily_rate')
        queryset = queryset.order_by(sort_field)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = CarSearchForm(self.request.GET or None)
        context['categories'] = CarCategory.objects.all()
        context['brands'] = CarBrand.objects.all()
        
        # Add filter parameters to context
        for param in ['city', 'category', 'transmission', 'fuel_type', 
                     'min_price', 'max_price', 'sort_by']:
            context[param] = self.request.GET.get(param, '')
        
        return context


class CarDetailView(DetailView):
    """Car details page."""
    model = Car
    template_name = 'cars/car_detail.html'
    context_object_name = 'car'
    
    def get_queryset(self):
        return Car.objects.filter(is_active=True).prefetch_related(
            'images', 'reviews'
        ).select_related('brand', 'category')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        car = self.object
        
        # Get reviews with pagination
        reviews = car.reviews.all().order_by('-created_at')
        paginator = Paginator(reviews, 5)
        page = self.request.GET.get('page')
        context['reviews'] = paginator.get_page(page)
        
        # Add review form if user is authenticated
        if self.request.user.is_authenticated:
            context['review_form'] = CarReviewForm()
        
        # Add booking form
        context['booking_form'] = CarBookingForm(
            initial={
                'car_id': str(car.id),
                'pickup_location': car.pickup_location,
                'dropoff_location': car.pickup_location
            }
        )
        
        # Calculate similar cars
        similar_cars = Car.objects.filter(
            category=car.category,
            is_active=True,
            status='AVAILABLE'
        ).exclude(id=car.id)[:4]
        context['similar_cars'] = similar_cars
        
        return context


@method_decorator(login_required, name='dispatch')
class CarBookingView(CreateView):
    """Handle car booking."""
    form_class = CarBookingForm
    template_name = 'cars/car_booking.html'
    
    def form_valid(self, form):
        # Get cleaned data
        car_id = form.cleaned_data['car_id']
        pickup_location = form.cleaned_data['pickup_location']
        dropoff_location = form.cleaned_data['dropoff_location']
        pickup_date = form.cleaned_data['pickup_date']
        dropoff_date = form.cleaned_data['dropoff_date']
        driver_age = form.cleaned_data['driver_age']
        extra_drivers = form.cleaned_data['extra_drivers']
        insurance_coverage = form.cleaned_data['insurance_coverage']
        special_requests = form.cleaned_data['special_requests']
        
        # Get car
        car = get_object_or_404(Car, id=car_id, is_active=True, status='AVAILABLE')
        
        # Calculate rental days
        rental_days = (dropoff_date - pickup_date).days
        if rental_days <= 0:
            form.add_error('dropoff_date', _('Drop-off date must be after pick-up date.'))
            return self.form_invalid(form)
        
        # Calculate price
        daily_rate = car.daily_rate
        if rental_days >= 30 and car.monthly_rate:
            total_price = car.monthly_rate * (rental_days // 30)
            remaining_days = rental_days % 30
            if remaining_days >= 7 and car.weekly_rate:
                total_price += car.weekly_rate * (remaining_days // 7)
                remaining_days = remaining_days % 7
            total_price += daily_rate * remaining_days
        elif rental_days >= 7 and car.weekly_rate:
            total_price = car.weekly_rate * (rental_days // 7)
            remaining_days = rental_days % 7
            total_price += daily_rate * remaining_days
        else:
            total_price = daily_rate * rental_days
        
        # Add insurance if selected
        if insurance_coverage:
            insurance_cost = total_price * Decimal('0.10')  # 10% of total
            total_price += insurance_cost
        
        # Add extra driver cost
        if extra_drivers:
            total_price += extra_drivers * Decimal('5.00') * rental_days
        
        # Create booking
        from apps.bookings.models import Booking
        
        booking = Booking.objects.create(
            user=self.request.user,
            service_type=Booking.ServiceType.CAR,
            service_id=car_id,
            check_in_date=pickup_date,
            check_out_date=dropoff_date,
            total_amount=total_price,
            status=Booking.Status.PENDING,
            metadata={
                'car_name': car.full_name,
                'registration_number': car.registration_number,
                'pickup_location': pickup_location,
                'dropoff_location': dropoff_location,
                'driver_age': driver_age,
                'extra_drivers': extra_drivers,
                'insurance_coverage': insurance_coverage,
                'rental_days': rental_days,
                'daily_rate': str(daily_rate),
                'special_requests': special_requests,
            }
        )
        
        # Update car status
        car.status = 'BOOKED'
        car.save()
        
        messages.success(
            self.request,
            _('Car booking created successfully! Please proceed to payment.')
        )
        
        # Store booking data in session for payment
        self.request.session['pending_booking'] = {
            'booking_id': str(booking.id),
            'service_type': 'CAR',
            'amount': str(total_price),
            'details': {
                'car_name': car.full_name,
                'pickup_date': pickup_date,
                'dropoff_date': dropoff_date,
                'rental_days': rental_days,
                'pickup_location': pickup_location,
                'dropoff_location': dropoff_location,
                'total_amount': total_price,
            }
        }
        
        return redirect('payments:create_payment')
    
    def form_invalid(self, form):
        messages.error(self.request, _('Please correct the errors below.'))
        return super().form_invalid(form)


@login_required
@require_http_methods(["POST"])
def submit_car_review(request, car_id):
    """Submit a car review."""
    car = get_object_or_404(Car, id=car_id, is_active=True)
    
    # Check if user has already reviewed
    existing_review = CarReview.objects.filter(
        car=car, 
        user=request.user
    ).first()
    
    if existing_review:
        messages.error(request, _('You have already reviewed this car.'))
        return redirect('cars:car_detail', pk=car_id)
    
    form = CarReviewForm(request.POST)
    if form.is_valid():
        review = form.save(commit=False)
        review.car = car
        review.user = request.user
        review.save()
        
        messages.success(request, _('Thank you for your review!'))
    else:
        messages.error(request, _('Please correct the errors in your review.'))
    
    return redirect('cars:car_detail', pk=car_id)


def car_availability_api(request):
    """API endpoint to check car availability."""
    if request.method == 'GET':
        car_id = request.GET.get('car_id')
        pickup_date = request.GET.get('pickup_date')
        dropoff_date = request.GET.get('dropoff_date')
        
        if not all([car_id, pickup_date, dropoff_date]):
            return JsonResponse({
                'success': False,
                'error': 'Missing required parameters'
            })
        
        try:
            car = Car.objects.get(id=car_id)
            pickup = datetime.strptime(pickup_date, '%Y-%m-%d').date()
            dropoff = datetime.strptime(dropoff_date, '%Y-%m-%d').date()
            
            # Check availability
            is_available = car.is_available_for_dates(pickup, dropoff)
            
            # Calculate price
            rental_days = (dropoff - pickup).days
            daily_rate = car.daily_rate
            total_price = daily_rate * rental_days
            
            # Apply discounts for longer rentals
            if rental_days >= 30 and car.monthly_rate:
                total_price = car.monthly_rate * (rental_days // 30)
                remaining_days = rental_days % 30
                if remaining_days >= 7 and car.weekly_rate:
                    total_price += car.weekly_rate * (remaining_days // 7)
                    remaining_days = remaining_days % 7
                total_price += daily_rate * remaining_days
            elif rental_days >= 7 and car.weekly_rate:
                total_price = car.weekly_rate * (rental_days // 7)
                remaining_days = rental_days % 7
                total_price += daily_rate * remaining_days
            
            return JsonResponse({
                'success': True,
                'available': is_available,
                'car_name': car.full_name,
                'rental_days': rental_days,
                'daily_rate': float(daily_rate),
                'weekly_rate': float(car.weekly_rate) if car.weekly_rate else None,
                'monthly_rate': float(car.monthly_rate) if car.monthly_rate else None,
                'total_price': float(total_price),
                'security_deposit': float(car.security_deposit),
                'km_limit_per_day': car.km_limit_per_day,
                'extra_km_charge': float(car.extra_km_charge),
            })
            
        except Car.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Car not found'})
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Invalid date format'})
    
    return JsonResponse({'success': False, 'error': 'Invalid method'})


class AdminCarListView(UserPassesTestMixin, ListView):
    """Car list for admin dashboard."""
    model = Car
    template_name = 'cars/admin/car_list.html'
    context_object_name = 'cars'
    paginate_by = 20
    
    def test_func(self):
        return self.request.user.is_admin
    
    def get_queryset(self):
        queryset = Car.objects.all().order_by('-created_at')
        
        # Filter by status
        status = self.request.GET.get('status', 'all')
        if status != 'all':
            queryset = queryset.filter(status=status)
        
        # Filter by city
        city = self.request.GET.get('city', '')
        if city:
            queryset = queryset.filter(city__icontains=city)
        
        # Search
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(registration_number__icontains=search) |
                Q(brand__name__icontains=search) |
                Q(model__icontains=search)
            )
        
        return queryset.select_related('brand', 'category')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_filter'] = self.request.GET.get('status', 'all')
        context['city_filter'] = self.request.GET.get('city', '')
        context['search_query'] = self.request.GET.get('search', '')
        return context


@login_required
@require_http_methods(["GET"])
def car_autocomplete(request):
    """Autocomplete for car search."""
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    cars = Car.objects.filter(
        Q(registration_number__icontains=query) |
        Q(brand__name__icontains=query) |
        Q(model__icontains=query),
        is_active=True,
        status='AVAILABLE'
    )[:10]
    
    results = []
    for car in cars:
        results.append({
            'id': str(car.id),
            'text': f"{car.brand.name} {car.model} ({car.registration_number}) - {car.city}",
            'brand': car.brand.name,
            'model': car.model,
            'registration': car.registration_number,
            'city': car.city,
            'daily_rate': float(car.daily_rate),
        })
    
    return JsonResponse({'results': results})
"""
Views for Hotel operations.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
import json

from .models import Hotel, HotelRoom, HotelReview, RoomType
from .services import HotelSearchService, HotelBookingService
from .forms import HotelSearchForm, HotelReviewForm, HotelBookingForm


class HotelListView(ListView):
    """List all hotels with search and filter options."""
    model = Hotel
    template_name = 'hotels/hotel_list.html'
    context_object_name = 'hotels'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Hotel.objects.filter(is_active=True).select_related()
        
        # Get filter parameters
        city = self.request.GET.get('city', '')
        min_price = self.request.GET.get('min_price')
        max_price = self.request.GET.get('max_price')
        rating = self.request.GET.get('rating')
        sort_by = self.request.GET.get('sort_by', 'rating')
        
        # Apply filters
        if city:
            queryset = queryset.filter(
                Q(city__icontains=city) | 
                Q(state__icontains=city) | 
                Q(country__icontains=city)
            )
        
        if rating:
            queryset = queryset.filter(star_rating__gte=int(rating))
        
        # Apply sorting
        sort_options = {
            'price_low': 'rooms__base_price',
            'price_high': '-rooms__base_price',
            'rating': '-avg_rating',
            'star': '-star_rating',
            'name': 'name',
        }
        sort_field = sort_options.get(sort_by, '-avg_rating')
        queryset = queryset.order_by(sort_field).distinct()
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = HotelSearchForm(self.request.GET or None)
        context['room_types'] = RoomType.objects.all()
        
        # Add filter parameters to context
        for param in ['city', 'min_price', 'max_price', 'rating', 'sort_by']:
            context[param] = self.request.GET.get(param, '')
        
        return context


class HotelDetailView(DetailView):
    """Hotel details page."""
    model = Hotel
    template_name = 'hotels/hotel_detail.html'
    context_object_name = 'hotel'
    
    def get_queryset(self):
        return Hotel.objects.filter(is_active=True).prefetch_related(
            'images', 'rooms', 'reviews'
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hotel = self.object
        
        # Get available room types
        context['room_types'] = hotel.rooms.filter(
            is_available=True,
            available_rooms__gt=0
        ).select_related('room_type').distinct()
        
        # Get reviews with pagination
        reviews = hotel.reviews.all().order_by('-created_at')
        paginator = Paginator(reviews, 5)
        page = self.request.GET.get('page')
        context['reviews'] = paginator.get_page(page)
        
        # Add review form if user is authenticated
        if self.request.user.is_authenticated:
            context['review_form'] = HotelReviewForm()
        
        # Add booking form
        context['booking_form'] = HotelBookingForm(
            initial={'hotel_id': str(hotel.id)}
        )
        
        return context


@method_decorator(login_required, name='dispatch')
class HotelBookingView(CreateView):
    """Handle hotel booking."""
    form_class = HotelBookingForm
    template_name = 'hotels/hotel_booking.html'
    
    def form_valid(self, form):
        hotel_id = form.cleaned_data['hotel_id']
        room_type_id = form.cleaned_data['room_type_id']
        check_in = form.cleaned_data['check_in']
        check_out = form.cleaned_data['check_out']
        rooms = form.cleaned_data['rooms']
        guests = form.cleaned_data['guests']
        special_requests = form.cleaned_data['special_requests']
        
        # Use booking service
        success, booking_data, error = HotelBookingService.create_booking(
            user=self.request.user,
            hotel_id=hotel_id,
            room_type_id=room_type_id,
            check_in=check_in,
            check_out=check_out,
            rooms=rooms,
            guests=guests,
            special_requests=special_requests
        )
        
        if success:
            messages.success(
                self.request,
                _('Booking created successfully! Please proceed to payment.')
            )
            # Store booking data in session for payment
            self.request.session['pending_booking'] = {
                'booking_id': booking_data['booking_id'],
                'service_type': 'HOTEL',
                'amount': str(booking_data['total_amount']),
                'details': booking_data
            }
            return redirect('payments:create_payment')
        else:
            messages.error(self.request, error)
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, _('Please correct the errors below.'))
        return super().form_invalid(form)


@login_required
@require_http_methods(["POST"])
def submit_review(request, hotel_id):
    """Submit a hotel review."""
    hotel = get_object_or_404(Hotel, id=hotel_id, is_active=True)
    
    # Check if user has already reviewed
    existing_review = HotelReview.objects.filter(
        hotel=hotel, 
        user=request.user
    ).first()
    
    if existing_review:
        messages.error(request, _('You have already reviewed this hotel.'))
        return redirect('hotels:hotel_detail', pk=hotel_id)
    
    form = HotelReviewForm(request.POST)
    if form.is_valid():
        review = form.save(commit=False)
        review.hotel = hotel
        review.user = request.user
        review.save()
        
        messages.success(request, _('Thank you for your review!'))
    else:
        messages.error(request, _('Please correct the errors in your review.'))
    
    return redirect('hotels:hotel_detail', pk=hotel_id)


class RoomAvailabilityView(TemplateView):
    """Check room availability."""
    template_name = 'hotels/room_availability.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hotel_id = self.request.GET.get('hotel_id')
        check_in = self.request.GET.get('check_in')
        check_out = self.request.GET.get('check_out')
        guests = self.request.GET.get('guests', 1)
        
        if hotel_id and check_in and check_out:
            try:
                hotel = Hotel.objects.get(id=hotel_id)
                rooms = HotelSearchService.get_available_rooms(
                    hotel_id=hotel_id,
                    check_in=check_in,
                    check_out=check_out,
                    guests=int(guests)
                )
                
                context['hotel'] = hotel
                context['rooms'] = rooms
                context['check_in'] = check_in
                context['check_out'] = check_out
                context['guests'] = guests
                
            except Hotel.DoesNotExist:
                messages.error(self.request, _('Hotel not found.'))
        
        return context


def search_hotels_api(request):
    """API endpoint for hotel search (for AJAX calls)."""
    if request.method == 'GET':
        city = request.GET.get('city', '')
        check_in = request.GET.get('check_in')
        check_out = request.GET.get('check_out')
        
        # Use search service
        results = HotelSearchService.search_hotels(
            city=city,
            check_in=check_in,
            check_out=check_out
        )
        
        # Format response
        hotels_data = []
        for hotel in results['hotels']:
            hotels_data.append({
                'id': str(hotel.id),
                'name': hotel.name,
                'city': hotel.city,
                'country': hotel.country,
                'star_rating': hotel.star_rating,
                'avg_rating': float(hotel.avg_rating),
                'thumbnail_url': hotel.thumbnail.url if hotel.thumbnail else None,
                'min_price': float(hotel.rooms.order_by('base_price').first().base_price) if hotel.rooms.exists() else 0,
            })
        
        return JsonResponse({
            'success': True,
            'hotels': hotels_data,
            'total': results['total'],
            'page': results['page'],
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid method'})


class AdminHotelListView(UserPassesTestMixin, ListView):
    """Hotel list for admin dashboard."""
    model = Hotel
    template_name = 'hotels/admin/hotel_list.html'
    context_object_name = 'hotels'
    paginate_by = 20
    
    def test_func(self):
        return self.request.user.is_admin
    
    def get_queryset(self):
        queryset = Hotel.objects.all().order_by('-created_at')
        
        # Filter by status
        status = self.request.GET.get('status', 'all')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        # Search
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(city__icontains=search) |
                Q(country__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_filter'] = self.request.GET.get('status', 'all')
        context['search_query'] = self.request.GET.get('search', '')
        return context


@login_required
@require_http_methods(["GET"])
def hotel_autocomplete(request):
    """Autocomplete for hotel search."""
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    hotels = Hotel.objects.filter(
        Q(name__icontains=query) |
        Q(city__icontains=query) |
        Q(country__icontains=query),
        is_active=True
    )[:10]
    
    results = []
    for hotel in hotels:
        results.append({
            'id': str(hotel.id),
            'text': f"{hotel.name}, {hotel.city}, {hotel.country}",
            'name': hotel.name,
            'city': hotel.city,
            'country': hotel.country,
        })
    
    return JsonResponse({'results': results})
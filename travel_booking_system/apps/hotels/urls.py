"""
URL configuration for hotels app.
"""

from django.urls import path
from . import views

app_name = 'hotels'

urlpatterns = [
    # Public views
    path('', views.HotelListView.as_view(), name='hotel_list'),
    path('search/', views.HotelListView.as_view(), name='hotel_search'),
    path('<uuid:pk>/', views.HotelDetailView.as_view(), name='hotel_detail'),
    path('<uuid:pk>/book/', views.HotelBookingView.as_view(), name='hotel_booking'),
    path('<uuid:hotel_id>/review/', views.submit_review, name='submit_review'),
    path('availability/', views.RoomAvailabilityView.as_view(), name='room_availability'),
    
    # API endpoints
    path('api/search/', views.search_hotels_api, name='search_hotels_api'),
    path('api/autocomplete/', views.hotel_autocomplete, name='hotel_autocomplete'),
    
    # Admin views
    path('admin/list/', views.AdminHotelListView.as_view(), name='admin_hotel_list'),
]
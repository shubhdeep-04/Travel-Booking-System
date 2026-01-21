"""
URL configuration for buses app.
"""

from django.urls import path
from . import views

app_name = 'buses'

urlpatterns = [
    # Public views
    path('', views.BusSearchView.as_view(), name='bus_search'),
    path('<uuid:pk>/', views.BusDetailView.as_view(), name='bus_detail'),
    path('<uuid:pk>/book/', views.BusBookingView.as_view(), name='bus_booking'),
    path('<uuid:bus_id>/review/', views.submit_bus_review, name='submit_review'),
    path('seats/', views.SeatSelectionView.as_view(), name='seat_selection'),
    
    # User bookings
    path('my-bookings/', views.MyBusBookingsView.as_view(), name='my_bookings'),
    path('my-bookings/<uuid:booking_id>/cancel/', views.cancel_bus_booking, name='cancel_booking'),
    
    # API endpoints
    path('api/availability/', views.bus_availability_api, name='bus_availability_api'),
    path('api/auto-allocate/', views.auto_allocate_seats_api, name='auto_allocate_seats'),
    path('api/routes/', views.bus_routes_api, name='bus_routes_api'),
    
    # Admin views
    path('admin/list/', views.AdminBusListView.as_view(), name='admin_bus_list'),
]
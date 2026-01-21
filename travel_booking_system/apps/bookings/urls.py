"""
URL configuration for bookings app.
"""

from django.urls import path
from . import views

app_name = 'bookings'

urlpatterns = [
    # User views
    path('', views.MyBookingsView.as_view(), name='my_bookings'),
    path('<uuid:pk>/', views.BookingDetailView.as_view(), name='booking_detail'),
    path('<uuid:booking_id>/cancel/', views.cancel_booking_view, name='cancel_booking'),
    path('<uuid:booking_id>/ticket/', views.download_ticket, name='download_ticket'),
    path('calendar/', views.BookingCalendarView.as_view(), name='booking_calendar'),
    path('invoice/<uuid:pk>/', views.BookingInvoiceView.as_view(), name='booking_invoice'),
    
    # API endpoints
    path('api/stats/', views.booking_stats_api, name='booking_stats_api'),
    
    # Admin views
    path('admin/list/', views.AdminBookingListView.as_view(), name='admin_booking_list'),
]
"""
URL configuration for trains app.
"""

from django.urls import path
from . import views

app_name = 'trains'

urlpatterns = [
    # Public views
    path('', views.TrainSearchView.as_view(), name='train_search'),
    path('search/', views.TrainSearchView.as_view(), name='train_search'),
    path('<uuid:pk>/', views.TrainDetailView.as_view(), name='train_detail'),
    path('<uuid:pk>/book/', views.TrainBookingView.as_view(), name='train_booking'),
    path('<uuid:train_id>/review/', views.submit_train_review, name='submit_review'),
    
    # User bookings
    path('my-bookings/', views.MyTrainBookingsView.as_view(), name='my_bookings'),
    path('my-bookings/<str:pnr_number>/', views.train_booking_detail, name='booking_detail'),
    path('my-bookings/<uuid:booking_id>/cancel/', views.cancel_train_booking, name='cancel_booking'),
    
    # API endpoints
    path('api/availability/', views.train_availability_api, name='train_availability_api'),
    path('api/schedule/', views.train_schedule_api, name='train_schedule_api'),
    
    # Admin views
    path('admin/list/', views.AdminTrainListView.as_view(), name='admin_train_list'),
]
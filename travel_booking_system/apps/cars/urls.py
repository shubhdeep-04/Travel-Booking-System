"""
URL configuration for cars app.
"""

from django.urls import path
from . import views

app_name = 'cars'

urlpatterns = [
    # Public views
    path('', views.CarListView.as_view(), name='car_list'),
    path('search/', views.CarListView.as_view(), name='car_search'),
    path('<uuid:pk>/', views.CarDetailView.as_view(), name='car_detail'),
    path('<uuid:pk>/book/', views.CarBookingView.as_view(), name='car_booking'),
    path('<uuid:car_id>/review/', views.submit_car_review, name='submit_car_review'),
    
    # API endpoints
    path('api/availability/', views.car_availability_api, name='car_availability_api'),
    path('api/autocomplete/', views.car_autocomplete, name='car_autocomplete'),
    
    # Admin views
    path('admin/list/', views.AdminCarListView.as_view(), name='admin_car_list'),
]
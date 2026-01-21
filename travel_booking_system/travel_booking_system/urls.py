"""
URL configuration for travel_booking_system project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # Home page
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    
    # User authentication (we'll create this in users app)
    path('users/', include('apps.users.urls')),
    
    # Service apps
    path('hotels/', include('apps.hotels.urls')),
    path('cars/', include('apps.cars.urls')),
    path('buses/', include('apps.buses.urls')),
    path('trains/', include('apps.trains.urls')),
    
    # Booking & Payment
    path('bookings/', include('apps.bookings.urls')),
    path('payments/', include('apps.payments.urls')),
    
    # Dashboard
    path('dashboard/', include('apps.dashboard.urls')),
    
    # API (for future)
    path('api-auth/', include('rest_framework.urls')),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # Debug toolbar
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns

# Admin site customization
admin.site.site_header = "Travel Booking System Admin"
admin.site.site_title = "Travel Booking Admin Portal"
admin.site.index_title = "Welcome to Travel Booking Admin Portal"
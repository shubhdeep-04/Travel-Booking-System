"""
URL configuration for dashboard app.
"""

from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Admin dashboard
    path('admin/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('admin/reports/', views.ReportsView.as_view(), name='admin_reports'),
    
    # User dashboard
    path('', views.UserDashboardView.as_view(), name='user_dashboard'),
    
    # API endpoints
    path('api/stats/', views.dashboard_stats_api, name='dashboard_stats_api'),
    path('api/reports/generate/', views.generate_report_api, name='generate_report_api'),
]
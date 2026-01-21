"""
Views for Admin Dashboard.
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
import json

from apps.bookings.models import Booking
from apps.payments.models import Payment
from apps.users.models import User
from apps.hotels.models import Hotel
from apps.cars.models import Car
from apps.buses.models import Bus
from apps.trains.models import Train
from .charts import DashboardCharts


class AdminDashboardView(UserPassesTestMixin, TemplateView):
    """Admin dashboard view."""
    template_name = 'dashboard/admin_dashboard.html'
    
    def test_func(self):
        return self.request.user.is_admin
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get date range (default: last 30 days)
        days = int(self.request.GET.get('days', 30))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Get dashboard data
        context.update(self.get_dashboard_data(start_date, end_date))
        context['days'] = days
        
        return context
    
    def get_dashboard_data(self, start_date, end_date):
        """Get all dashboard data for the period."""
        
        # Bookings data
        bookings = Booking.objects.filter(
            booking_date__date__range=[start_date, end_date]
        )
        
        total_bookings = bookings.count()
        confirmed_bookings = bookings.filter(status='CONFIRMED').count()
        cancelled_bookings = bookings.filter(status='CANCELLED').count()
        booking_revenue = bookings.filter(
            status__in=['CONFIRMED', 'COMPLETED']
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Payments data
        payments = Payment.objects.filter(
            initiated_at__date__range=[start_date, end_date]
        )
        
        total_payments = payments.count()
        completed_payments = payments.filter(status='COMPLETED').count()
        payment_amount = payments.filter(status='COMPLETED').aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        # Users data
        total_users = User.objects.count()
        new_users = User.objects.filter(
            date_joined__date__range=[start_date, end_date]
        ).count()
        active_users = User.objects.filter(
            last_login__date__gte=end_date - timedelta(days=7)
        ).count()
        
        # Services data
        total_hotels = Hotel.objects.count()
        active_hotels = Hotel.objects.filter(is_active=True).count()
        
        total_cars = Car.objects.filter(is_active=True).count()
        available_cars = Car.objects.filter(status='AVAILABLE').count()
        
        total_buses = Bus.objects.filter(status='ACTIVE').count()
        total_trains = Train.objects.filter(status='ACTIVE').count()
        
        # Recent bookings
        recent_bookings = bookings.select_related('user').order_by('-booking_date')[:10]
        
        # Recent payments
        recent_payments = payments.select_related('booking', 'booking__user').order_by('-initiated_at')[:10]
        
        # Chart data
        chart_generator = DashboardCharts()
        
        # Daily bookings chart
        daily_bookings_chart = chart_generator.daily_bookings_chart(start_date, end_date)
        
        # Revenue chart
        revenue_chart = chart_generator.revenue_chart(start_date, end_date)
        
        # Service distribution chart
        service_chart = chart_generator.service_distribution_chart(start_date, end_date)
        
        # Payment method chart
        payment_method_chart = chart_generator.payment_method_chart(start_date, end_date)
        
        # Top performing services
        top_services = chart_generator.top_services(start_date, end_date)
        
        # Booking status distribution
        status_distribution = chart_generator.booking_status_distribution(start_date, end_date)
        
        return {
            # Summary cards
            'summary': {
                'total_bookings': total_bookings,
                'confirmed_bookings': confirmed_bookings,
                'cancelled_bookings': cancelled_bookings,
                'booking_revenue': booking_revenue,
                
                'total_payments': total_payments,
                'completed_payments': completed_payments,
                'payment_amount': payment_amount,
                'payment_success_rate': (completed_payments / total_payments * 100) if total_payments > 0 else 0,
                
                'total_users': total_users,
                'new_users': new_users,
                'active_users': active_users,
                'user_growth_rate': (new_users / total_users * 100) if total_users > 0 else 0,
                
                'total_hotels': total_hotels,
                'active_hotels': active_hotels,
                'total_cars': total_cars,
                'available_cars': available_cars,
                'total_buses': total_buses,
                'total_trains': total_trains,
            },
            
            # Recent activity
            'recent_bookings': recent_bookings,
            'recent_payments': recent_payments,
            
            # Chart data
            'daily_bookings_chart': json.dumps(daily_bookings_chart),
            'revenue_chart': json.dumps(revenue_chart),
            'service_chart': json.dumps(service_chart),
            'payment_method_chart': json.dumps(payment_method_chart),
            
            # Additional data
            'top_services': top_services,
            'status_distribution': status_distribution,
            
            # Date range
            'date_range': {
                'start': start_date,
                'end': end_date,
                'days': (end_date - start_date).days,
            }
        }


class UserDashboardView(LoginRequiredMixin, TemplateView):
    """User dashboard view."""
    template_name = 'dashboard/user_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get user's bookings
        bookings = Booking.objects.filter(user=user)
        
        # Recent bookings
        recent_bookings = bookings.order_by('-booking_date')[:5]
        
        # Upcoming bookings
        upcoming_bookings = bookings.filter(
            status='CONFIRMED'
        ).filter(
            Q(check_in_date__gte=timezone.now().date()) |
            Q(travel_date__gte=timezone.now().date())
        ).order_by('check_in_date', 'travel_date')[:5]
        
        # Booking statistics
        total_bookings = bookings.count()
        confirmed_bookings = bookings.filter(status='CONFIRMED').count()
        cancelled_bookings = bookings.filter(status='CANCELLED').count()
        total_spent = bookings.filter(
            status__in=['CONFIRMED', 'COMPLETED']
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Favorite service type
        favorite_service = bookings.values('service_type').annotate(
            count=Count('id')
        ).order_by('-count').first()
        
        # Wallet balance
        from apps.payments.models import Wallet
        try:
            wallet = Wallet.objects.get(user=user)
            wallet_balance = wallet.balance
        except Wallet.DoesNotExist:
            wallet_balance = 0
        
        context.update({
            'recent_bookings': recent_bookings,
            'upcoming_bookings': upcoming_bookings,
            'total_bookings': total_bookings,
            'confirmed_bookings': confirmed_bookings,
            'cancelled_bookings': cancelled_bookings,
            'total_spent': total_spent,
            'favorite_service': favorite_service,
            'wallet_balance': wallet_balance,
        })
        
        return context


@login_required
def dashboard_stats_api(request):
    """API endpoint for dashboard statistics."""
    if request.method == 'GET':
        user = request.user
        
        if user.is_admin:
            # Admin dashboard stats
            days = int(request.GET.get('days', 7))
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=days)
            
            # Get stats
            bookings = Booking.objects.filter(
                booking_date__date__range=[start_date, end_date]
            )
            
            payments = Payment.objects.filter(
                initiated_at__date__range=[start_date, end_date]
            )
            
            stats = {
                'bookings': {
                    'total': bookings.count(),
                    'confirmed': bookings.filter(status='CONFIRMED').count(),
                    'revenue': float(bookings.filter(
                        status__in=['CONFIRMED', 'COMPLETED']
                    ).aggregate(total=Sum('total_amount'))['total'] or 0),
                },
                'payments': {
                    'total': payments.count(),
                    'completed': payments.filter(status='COMPLETED').count(),
                    'amount': float(payments.filter(status='COMPLETED').aggregate(
                        total=Sum('amount')
                    )['total'] or 0),
                },
                'users': {
                    'total': User.objects.count(),
                    'new': User.objects.filter(
                        date_joined__date__range=[start_date, end_date]
                    ).count(),
                },
            }
            
            return JsonResponse({'success': True, 'stats': stats})
        
        else:
            # User dashboard stats
            bookings = Booking.objects.filter(user=user)
            
            stats = {
                'total_bookings': bookings.count(),
                'upcoming_bookings': bookings.filter(
                    status='CONFIRMED'
                ).filter(
                    Q(check_in_date__gte=timezone.now().date()) |
                    Q(travel_date__gte=timezone.now().date())
                ).count(),
                'total_spent': float(bookings.filter(
                    status__in=['CONFIRMED', 'COMPLETED']
                ).aggregate(total=Sum('total_amount'))['total'] or 0),
            }
            
            return JsonResponse({'success': True, 'stats': stats})
    
    return JsonResponse({'success': False, 'error': 'Invalid method'})


class ReportsView(UserPassesTestMixin, TemplateView):
    """Reports view for admin."""
    template_name = 'dashboard/reports.html'
    
    def test_func(self):
        return self.request.user.is_admin
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get report type and date range
        report_type = self.request.GET.get('type', 'bookings')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if not date_from or not date_to:
            # Default to last month
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=30)
            date_from = start_date.isoformat()
            date_to = end_date.isoformat()
        
        context.update({
            'report_type': report_type,
            'date_from': date_from,
            'date_to': date_to,
        })
        
        return context


@login_required
def generate_report_api(request):
    """API endpoint to generate reports."""
    if request.method == 'GET' and request.user.is_admin:
        report_type = request.GET.get('type', 'bookings')
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        
        if not date_from or not date_to:
            return JsonResponse({
                'success': False,
                'error': 'Date range is required'
            })
        
        try:
            start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            end_date = datetime.strptime(date_to, '%Y-%m-%d').date()
            
            chart_generator = DashboardCharts()
            
            if report_type == 'bookings':
                report_data = chart_generator.booking_report(start_date, end_date)
            elif report_type == 'revenue':
                report_data = chart_generator.revenue_report(start_date, end_date)
            elif report_type == 'users':
                report_data = chart_generator.user_report(start_date, end_date)
            elif report_type == 'services':
                report_data = chart_generator.service_report(start_date, end_date)
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid report type'
                })
            
            return JsonResponse({
                'success': True,
                'report': report_data
            })
            
        except ValueError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid date format'
            })
    
    return JsonResponse({
        'success': False,
        'error': 'Unauthorized'
    })
"""
Chart generation for Dashboard.
"""

from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
import json


class DashboardCharts:
    """Generate charts for dashboard."""
    
    def daily_bookings_chart(self, start_date, end_date):
        """Generate daily bookings chart data."""
        from apps.bookings.models import Booking
        
        # Get daily bookings count
        daily_data = Booking.objects.filter(
            booking_date__date__range=[start_date, end_date]
        ).extra(
            select={'day': 'DATE(booking_date)'}
        ).values('day').annotate(
            count=Count('id')
        ).order_by('day')
        
        # Format for Chart.js
        labels = []
        data = []
        
        # Fill in missing dates
        current_date = start_date
        while current_date <= end_date:
            labels.append(current_date.strftime('%Y-%m-%d'))
            
            # Find data for this date
            day_data = next((item for item in daily_data if item['day'] == current_date), None)
            data.append(day_data['count'] if day_data else 0)
            
            current_date += timedelta(days=1)
        
        chart_data = {
            'labels': labels,
            'datasets': [{
                'label': 'Daily Bookings',
                'data': data,
                'borderColor': 'rgb(75, 192, 192)',
                'backgroundColor': 'rgba(75, 192, 192, 0.2)',
                'tension': 0.1
            }]
        }
        
        return chart_data
    
    def revenue_chart(self, start_date, end_date):
        """Generate revenue chart data."""
        from apps.bookings.models import Booking
        
        # Get daily revenue
        daily_data = Booking.objects.filter(
            booking_date__date__range=[start_date, end_date],
            status__in=['CONFIRMED', 'COMPLETED']
        ).extra(
            select={'day': 'DATE(booking_date)'}
        ).values('day').annotate(
            revenue=Sum('total_amount')
        ).order_by('day')
        
        # Format for Chart.js
        labels = []
        data = []
        
        # Fill in missing dates
        current_date = start_date
        while current_date <= end_date:
            labels.append(current_date.strftime('%Y-%m-%d'))
            
            # Find data for this date
            day_data = next((item for item in daily_data if item['day'] == current_date), None)
            data.append(float(day_data['revenue']) if day_data else 0)
            
            current_date += timedelta(days=1)
        
        chart_data = {
            'labels': labels,
            'datasets': [{
                'label': 'Daily Revenue ($)',
                'data': data,
                'borderColor': 'rgb(54, 162, 235)',
                'backgroundColor': 'rgba(54, 162, 235, 0.2)',
                'tension': 0.1
            }]
        }
        
        return chart_data
    
    def service_distribution_chart(self, start_date, end_date):
        """Generate service distribution chart data."""
        from apps.bookings.models import Booking
        
        # Get bookings by service type
        service_data = Booking.objects.filter(
            booking_date__date__range=[start_date, end_date]
        ).values('service_type').annotate(
            count=Count('id'),
            revenue=Sum('total_amount')
        ).order_by('-count')
        
        # Format for Chart.js
        labels = [item['service_type'] for item in service_data]
        counts = [item['count'] for item in service_data]
        revenues = [float(item['revenue'] or 0) for item in service_data]
        
        # Colors for different services
        service_colors = {
            'HOTEL': 'rgb(255, 99, 132)',
            'CAR': 'rgb(54, 162, 235)',
            'BUS': 'rgb(255, 205, 86)',
            'TRAIN': 'rgb(75, 192, 192)',
        }
        
        background_colors = [service_colors.get(label, 'rgb(201, 203, 207)') for label in labels]
        
        chart_data = {
            'labels': labels,
            'datasets': [{
                'label': 'Bookings by Service',
                'data': counts,
                'backgroundColor': background_colors,
                'borderWidth': 1
            }]
        }
        
        return chart_data
    
    def payment_method_chart(self, start_date, end_date):
        """Generate payment method distribution chart."""
        from apps.payments.models import Payment
        
        # Get payments by method
        method_data = Payment.objects.filter(
            initiated_at__date__range=[start_date, end_date],
            status='COMPLETED'
        ).values('payment_method').annotate(
            count=Count('id'),
            amount=Sum('amount')
        ).order_by('-count')
        
        # Format for Chart.js
        labels = [self._format_payment_method(item['payment_method']) for item in method_data]
        counts = [item['count'] for item in method_data]
        amounts = [float(item['amount'] or 0) for item in method_data]
        
        # Colors for different payment methods
        method_colors = {
            'CREDIT_CARD': 'rgb(255, 99, 132)',
            'DEBIT_CARD': 'rgb(54, 162, 235)',
            'UPI': 'rgb(255, 205, 86)',
            'NET_BANKING': 'rgb(75, 192, 192)',
            'WALLET': 'rgb(153, 102, 255)',
            'CASH': 'rgb(201, 203, 207)',
        }
        
        background_colors = [method_colors.get(item['payment_method'], 'rgb(201, 203, 207)') for item in method_data]
        
        chart_data = {
            'labels': labels,
            'datasets': [{
                'label': 'Payments by Method',
                'data': amounts,
                'backgroundColor': background_colors,
                'borderWidth': 1
            }]
        }
        
        return chart_data
    
    def booking_status_distribution(self, start_date, end_date):
        """Get booking status distribution."""
        from apps.bookings.models import Booking
        
        status_data = Booking.objects.filter(
            booking_date__date__range=[start_date, end_date]
        ).values('status').annotate(
            count=Count('id'),
            percentage=Count('id') * 100.0 / Count('id', filter=models.Q(booking_date__date__range=[start_date, end_date]))
        ).order_by('-count')
        
        return list(status_data)
    
    def top_services(self, start_date, end_date, limit=5):
        """Get top performing services."""
        from apps.bookings.models import Booking
        
        # Get top hotels
        top_hotels = Booking.objects.filter(
            service_type='HOTEL',
            booking_date__date__range=[start_date, end_date],
            status__in=['CONFIRMED', 'COMPLETED']
        ).values('metadata__hotel_name').annotate(
            bookings=Count('id'),
            revenue=Sum('total_amount')
        ).order_by('-revenue')[:limit]
        
        # Get top cars
        top_cars = Booking.objects.filter(
            service_type='CAR',
            booking_date__date__range=[start_date, end_date],
            status__in=['CONFIRMED', 'COMPLETED']
        ).values('metadata__car_model').annotate(
            bookings=Count('id'),
            revenue=Sum('total_amount')
        ).order_by('-revenue')[:limit]
        
        return {
            'hotels': list(top_hotels),
            'cars': list(top_cars),
        }
    
    def booking_report(self, start_date, end_date):
        """Generate comprehensive booking report."""
        from apps.bookings.models import Booking
        
        bookings = Booking.objects.filter(
            booking_date__date__range=[start_date, end_date]
        )
        
        # Overall statistics
        overall = bookings.aggregate(
            total=Count('id'),
            confirmed=Count('id', filter=models.Q(status='CONFIRMED')),
            cancelled=Count('id', filter=models.Q(status='CANCELLED')),
            revenue=Sum('total_amount', filter=models.Q(status__in=['CONFIRMED', 'COMPLETED'])),
            avg_booking_value=Avg('total_amount', filter=models.Q(status__in=['CONFIRMED', 'COMPLETED'])),
        )
        
        # By service type
        by_service = list(bookings.values('service_type').annotate(
            count=Count('id'),
            revenue=Sum('total_amount'),
            avg_value=Avg('total_amount')
        ).order_by('-revenue'))
        
        # By status
        by_status = list(bookings.values('status').annotate(
            count=Count('id'),
            percentage=Count('id') * 100.0 / bookings.count()
        ).order_by('-count'))
        
        # Daily breakdown
        daily_breakdown = list(bookings.extra(
            select={'day': 'DATE(booking_date)'}
        ).values('day').annotate(
            bookings=Count('id'),
            revenue=Sum('total_amount')
        ).order_by('day'))
        
        return {
            'period': {
                'start': start_date,
                'end': end_date,
            },
            'overall': overall,
            'by_service': by_service,
            'by_status': by_status,
            'daily_breakdown': daily_breakdown,
        }
    
    def revenue_report(self, start_date, end_date):
        """Generate revenue report."""
        from apps.bookings.models import Booking
        
        bookings = Booking.objects.filter(
            booking_date__date__range=[start_date, end_date],
            status__in=['CONFIRMED', 'COMPLETED']
        )
        
        # Revenue statistics
        revenue_stats = bookings.aggregate(
            total_revenue=Sum('total_amount'),
            avg_revenue_per_booking=Avg('total_amount'),
            max_booking=Max('total_amount'),
            min_booking=Min('total_amount'),
        )
        
        # Revenue by service
        revenue_by_service = list(bookings.values('service_type').annotate(
            revenue=Sum('total_amount'),
            percentage=Sum('total_amount') * 100.0 / revenue_stats['total_revenue']
        ).order_by('-revenue'))
        
        # Monthly revenue trend
        monthly_revenue = list(bookings.extra(
            select={'month': "DATE_FORMAT(booking_date, '%%Y-%%m')"}
        ).values('month').annotate(
            revenue=Sum('total_amount')
        ).order_by('month'))
        
        return {
            'period': {
                'start': start_date,
                'end': end_date,
            },
            'revenue_stats': revenue_stats,
            'revenue_by_service': revenue_by_service,
            'monthly_revenue': monthly_revenue,
        }
    
    def user_report(self, start_date, end_date):
        """Generate user report."""
        from apps.users.models import User
        from apps.bookings.models import Booking
        
        # User statistics
        users = User.objects.filter(date_joined__date__range=[start_date, end_date])
        
        user_stats = users.aggregate(
            total=Count('id'),
            active=Count('id', filter=models.Q(last_login__date__gte=start_date)),
            avg_age=Avg('age'),  # Assuming age field exists
        )
        
        # User registration trend
        registration_trend = list(users.extra(
            select={'day': 'DATE(date_joined)'}
        ).values('day').annotate(
            registrations=Count('id')
        ).order_by('day'))
        
        # Top users by bookings
        top_users = Booking.objects.filter(
            booking_date__date__range=[start_date, end_date]
        ).values('user__username', 'user__email').annotate(
            bookings=Count('id'),
            revenue=Sum('total_amount')
        ).order_by('-revenue')[:10]
        
        return {
            'period': {
                'start': start_date,
                'end': end_date,
            },
            'user_stats': user_stats,
            'registration_trend': registration_trend,
            'top_users': list(top_users),
        }
    
    def service_report(self, start_date, end_date):
        """Generate service performance report."""
        from apps.hotels.models import Hotel, HotelRoom
        from apps.cars.models import Car
        from apps.buses.models import Bus
        from apps.trains.models import Train
        from apps.bookings.models import Booking
        
        # Hotel performance
        hotel_bookings = Booking.objects.filter(
            service_type='HOTEL',
            booking_date__date__range=[start_date, end_date]
        )
        
        hotel_stats = {
            'total_bookings': hotel_bookings.count(),
            'revenue': hotel_bookings.aggregate(total=Sum('total_amount'))['total'] or 0,
            'avg_nights': hotel_bookings.aggregate(avg=Avg('metadata__nights'))['avg'] or 0,
            'occupancy_rate': self._calculate_hotel_occupancy(start_date, end_date),
        }
        
        # Car performance
        car_bookings = Booking.objects.filter(
            service_type='CAR',
            booking_date__date__range=[start_date, end_date]
        )
        
        car_stats = {
            'total_bookings': car_bookings.count(),
            'revenue': car_bookings.aggregate(total=Sum('total_amount'))['total'] or 0,
            'avg_days': car_bookings.aggregate(avg=Avg('metadata__rental_days'))['avg'] or 0,
            'utilization_rate': self._calculate_car_utilization(start_date, end_date),
        }
        
        # Bus performance
        bus_bookings = Booking.objects.filter(
            service_type='BUS',
            booking_date__date__range=[start_date, end_date]
        )
        
        bus_stats = {
            'total_bookings': bus_bookings.count(),
            'revenue': bus_bookings.aggregate(total=Sum('total_amount'))['total'] or 0,
            'avg_seats': bus_bookings.aggregate(avg=Avg('metadata__seats'))['avg'] or 0,
            'load_factor': self._calculate_bus_load_factor(start_date, end_date),
        }
        
        # Train performance
        train_bookings = Booking.objects.filter(
            service_type='TRAIN',
            booking_date__date__range=[start_date, end_date]
        )
        
        train_stats = {
            'total_bookings': train_bookings.count(),
            'revenue': train_bookings.aggregate(total=Sum('total_amount'))['total'] or 0,
            'avg_passengers': train_bookings.aggregate(avg=Avg('total_passengers'))['avg'] or 1,
        }
        
        return {
            'period': {
                'start': start_date,
                'end': end_date,
            },
            'hotels': hotel_stats,
            'cars': car_stats,
            'buses': bus_stats,
            'trains': train_stats,
        }
    
    def _format_payment_method(self, method):
        """Format payment method for display."""
        method_names = {
            'CREDIT_CARD': 'Credit Card',
            'DEBIT_CARD': 'Debit Card',
            'UPI': 'UPI',
            'NET_BANKING': 'Net Banking',
            'WALLET': 'Wallet',
            'CASH': 'Cash',
            'BANK_TRANSFER': 'Bank Transfer',
        }
        return method_names.get(method, method)
    
    def _calculate_hotel_occupancy(self, start_date, end_date):
        """Calculate hotel occupancy rate."""
        from apps.hotels.models import HotelRoom
        from apps.bookings.models import Booking
        
        # Simplified calculation
        total_rooms = HotelRoom.objects.filter(is_available=True).count()
        
        if total_rooms == 0:
            return 0
        
        # Get booked room nights in period
        hotel_bookings = Booking.objects.filter(
            service_type='HOTEL',
            booking_date__date__range=[start_date, end_date],
            status__in=['CONFIRMED', 'COMPLETED']
        )
        
        booked_nights = 0
        for booking in hotel_bookings:
            nights = booking.metadata.get('nights', 1)
            rooms = booking.metadata.get('rooms', 1)
            booked_nights += nights * rooms
        
        # Calculate occupancy rate
        days_in_period = (end_date - start_date).days + 1
        total_room_nights = total_rooms * days_in_period
        
        if total_room_nights == 0:
            return 0
        
        return (booked_nights / total_room_nights) * 100
    
    def _calculate_car_utilization(self, start_date, end_date):
        """Calculate car utilization rate."""
        from apps.cars.models import Car
        from apps.bookings.models import Booking
        
        total_cars = Car.objects.filter(is_active=True).count()
        
        if total_cars == 0:
            return 0
        
        # Get booked car days in period
        car_bookings = Booking.objects.filter(
            service_type='CAR',
            booking_date__date__range=[start_date, end_date],
            status__in=['CONFIRMED', 'COMPLETED']
        )
        
        booked_days = 0
        for booking in car_bookings:
            days = booking.metadata.get('rental_days', 1)
            booked_days += days
        
        # Calculate utilization rate
        days_in_period = (end_date - start_date).days + 1
        total_car_days = total_cars * days_in_period
        
        if total_car_days == 0:
            return 0
        
        return (booked_days / total_car_days) * 100
    
    def _calculate_bus_load_factor(self, start_date, end_date):
        """Calculate bus load factor."""
        from apps.buses.models import Bus
        from apps.bookings.models import Booking
        
        total_buses = Bus.objects.filter(status='ACTIVE').count()
        
        if total_buses == 0:
            return 0
        
        # Get total seats booked
        bus_bookings = Booking.objects.filter(
            service_type='BUS',
            booking_date__date__range=[start_date, end_date],
            status__in=['CONFIRMED', 'COMPLETED']
        )
        
        total_seats_booked = 0
        total_seats_available = 0
        
        for bus in Bus.objects.filter(status='ACTIVE'):
            total_seats_available += bus.total_seats
        
        for booking in bus_bookings:
            seats = len(booking.metadata.get('seat_numbers', []))
            total_seats_booked += seats
        
        if total_seats_available == 0:
            return 0
        
        return (total_seats_booked / total_seats_available) * 100
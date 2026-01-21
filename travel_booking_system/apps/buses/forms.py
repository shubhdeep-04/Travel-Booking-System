"""
Forms for Bus operations.
"""

from django import forms
from django.utils.translation import gettext_lazy as _
from datetime import date, timedelta

from .models import Bus, BusBooking, BusReview, BusType


class BusSearchForm(forms.Form):
    """Form for searching buses."""
    route_from = forms.CharField(
        label=_('From'),
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter departure city'),
            'id': 'busFrom'
        })
    )
    route_to = forms.CharField(
        label=_('To'),
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter destination city'),
            'id': 'busTo'
        })
    )
    travel_date = forms.DateField(
        label=_('Travel Date'),
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'min': date.today().isoformat()
        })
    )
    bus_type = forms.ModelChoiceField(
        label=_('Bus Type'),
        queryset=BusType.objects.all(),
        required=False,
        empty_label=_('All Types'),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        route_from = cleaned_data.get('route_from')
        route_to = cleaned_data.get('route_to')
        travel_date = cleaned_data.get('travel_date')
        
        if route_from and route_to:
            if route_from.lower() == route_to.lower():
                raise forms.ValidationError(_('Departure and destination cannot be the same.'))
        
        if travel_date:
            if travel_date < date.today():
                raise forms.ValidationError(_('Travel date cannot be in the past.'))
            
            # Maximum advance booking (e.g., 90 days)
            max_advance_days = 90
            if travel_date > date.today() + timedelta(days=max_advance_days):
                raise forms.ValidationError(
                    _(f'Maximum advance booking is {max_advance_days} days.')
                )
        
        return cleaned_data


class BusBookingForm(forms.Form):
    """Form for booking bus tickets."""
    bus_id = forms.UUIDField(widget=forms.HiddenInput())
    travel_date = forms.DateField(
        label=_('Travel Date'),
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'min': date.today().isoformat()
        })
    )
    seats = forms.CharField(
        label=_('Selected Seats'),
        widget=forms.HiddenInput()
    )
    
    # Passenger Information
    passenger_name = forms.CharField(
        label=_('Passenger Name'),
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter passenger name as per ID')
        })
    )
    passenger_age = forms.IntegerField(
        label=_('Passenger Age'),
        min_value=1,
        max_value=120,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1,
            'max': 120
        })
    )
    passenger_gender = forms.ChoiceField(
        label=_('Passenger Gender'),
        choices=[('MALE', 'Male'), ('FEMALE', 'Female'), ('OTHER', 'Other')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    passenger_phone = forms.CharField(
        label=_('Passenger Phone'),
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter contact number')
        })
    )
    passenger_email = forms.EmailField(
        label=_('Passenger Email'),
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter email address')
        })
    )
    
    # Boarding/Dropping Points
    boarding_point = forms.CharField(
        label=_('Boarding Point'),
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Select boarding point')
        })
    )
    dropping_point = forms.CharField(
        label=_('Dropping Point'),
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Select dropping point')
        })
    )
    
    # Special Requests
    special_requests = forms.CharField(
        label=_('Special Requests'),
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': _('Any special requests...')
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        travel_date = cleaned_data.get('travel_date')
        seats = cleaned_data.get('seats')
        
        # Validate travel date
        if travel_date:
            if travel_date < date.today():
                self.add_error('travel_date', _('Travel date cannot be in the past.'))
            
            # Check if date is too far in future
            max_advance_days = 90
            if travel_date > date.today() + timedelta(days=max_advance_days):
                self.add_error('travel_date', 
                    _(f'Maximum advance booking is {max_advance_days} days.'))
        
        # Validate seats
        if seats:
            try:
                seat_list = seats.split(',')
                if len(seat_list) > 6:  # Max 6 seats per booking
                    self.add_error('seats', _('Maximum 6 seats per booking.'))
            except:
                self.add_error('seats', _('Invalid seat selection.'))
        
        return cleaned_data


class BusReviewForm(forms.ModelForm):
    """Form for submitting bus reviews."""
    
    class Meta:
        model = BusReview
        fields = ['rating', 'title', 'comment', 'cleanliness', 'comfort', 
                 'punctuality', 'staff_behavior', 'value_for_money']
        widgets = {
            'rating': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Title of your review')
            }),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _('Share your experience...')
            }),
            'cleanliness': forms.Select(attrs={'class': 'form-control'}),
            'comfort': forms.Select(attrs={'class': 'form-control'}),
            'punctuality': forms.Select(attrs={'class': 'form-control'}),
            'staff_behavior': forms.Select(attrs={'class': 'form-control'}),
            'value_for_money': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'rating': _('Overall Rating'),
            'cleanliness': _('Cleanliness'),
            'comfort': _('Comfort'),
            'punctuality': _('Punctuality'),
            'staff_behavior': _('Staff Behavior'),
            'value_for_money': _('Value for Money'),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set rating choices
        self.fields['rating'].choices = BusReview.Rating.choices
        for field in ['cleanliness', 'comfort', 'punctuality', 'staff_behavior', 'value_for_money']:
            self.fields[field].choices = [
                (i, '★' * i) for i in range(1, 6)
            ]


class BusAdminForm(forms.ModelForm):
    """Form for admin to manage buses."""
    
    class Meta:
        model = Bus
        fields = '__all__'
        widgets = {
            'bus_number': forms.TextInput(attrs={'class': 'form-control'}),
            'operator': forms.Select(attrs={'class': 'form-control'}),
            'bus_type': forms.Select(attrs={'class': 'form-control'}),
            'route_from': forms.TextInput(attrs={'class': 'form-control'}),
            'route_to': forms.TextInput(attrs={'class': 'form-control'}),
            'via_cities': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'distance_km': forms.NumberInput(attrs={'class': 'form-control'}),
            'departure_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'arrival_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'duration_hours': forms.NumberInput(attrs={'class': 'form-control'}),
            'total_seats': forms.NumberInput(attrs={'class': 'form-control'}),
            'seats_per_row': forms.NumberInput(attrs={'class': 'form-control'}),
            'seat_layout': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'base_fare': forms.NumberInput(attrs={'class': 'form-control'}),
            'tax_percentage': forms.NumberInput(attrs={'class': 'form-control'}),
            'cancellation_before_hours': forms.NumberInput(attrs={'class': 'form-control'}),
            'cancellation_charge_percentage': forms.NumberInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
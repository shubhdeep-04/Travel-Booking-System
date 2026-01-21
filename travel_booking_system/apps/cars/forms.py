"""
Forms for Car operations.
"""

from django import forms
from django.utils.translation import gettext_lazy as _
from datetime import date, timedelta

from .models import Car, CarReview, CarCategory, CarBrand


class CarSearchForm(forms.Form):
    """Form for searching cars."""
    city = forms.CharField(
        label=_('City'),
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter city name')
        })
    )
    pickup_date = forms.DateField(
        label=_('Pick-up Date'),
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'min': date.today().isoformat()
        })
    )
    dropoff_date = forms.DateField(
        label=_('Drop-off Date'),
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'min': (date.today() + timedelta(days=1)).isoformat()
        })
    )
    category = forms.ModelChoiceField(
        label=_('Category'),
        queryset=CarCategory.objects.all(),
        required=False,
        empty_label=_('All Categories'),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        pickup_date = cleaned_data.get('pickup_date')
        dropoff_date = cleaned_data.get('dropoff_date')
        
        if pickup_date and dropoff_date:
            if pickup_date < date.today():
                raise forms.ValidationError(_('Pick-up date cannot be in the past.'))
            if dropoff_date <= pickup_date:
                raise forms.ValidationError(_('Drop-off date must be after pick-up date.'))
        
        return cleaned_data


class CarBookingForm(forms.Form):
    """Form for booking a car."""
    car_id = forms.UUIDField(widget=forms.HiddenInput())
    
    pickup_location = forms.CharField(
        label=_('Pick-up Location'),
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter pick-up location')
        })
    )
    dropoff_location = forms.CharField(
        label=_('Drop-off Location'),
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter drop-off location (same as pick-up if empty)')
        })
    )
    pickup_date = forms.DateField(
        label=_('Pick-up Date'),
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'min': date.today().isoformat()
        })
    )
    dropoff_date = forms.DateField(
        label=_('Drop-off Date'),
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'min': (date.today() + timedelta(days=1)).isoformat()
        })
    )
    pickup_time = forms.TimeField(
        label=_('Pick-up Time'),
        widget=forms.TimeInput(attrs={
            'class': 'form-control',
            'type': 'time'
        })
    )
    dropoff_time = forms.TimeField(
        label=_('Drop-off Time'),
        widget=forms.TimeInput(attrs={
            'class': 'form-control',
            'type': 'time'
        })
    )
    driver_age = forms.IntegerField(
        label=_('Driver Age'),
        min_value=18,
        max_value=100,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 18,
            'max': 100
        })
    )
    extra_drivers = forms.IntegerField(
        label=_('Additional Drivers'),
        required=False,
        initial=0,
        min_value=0,
        max_value=3,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 0,
            'max': 3
        })
    )
    insurance_coverage = forms.BooleanField(
        label=_('Add Insurance Coverage'),
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    special_requests = forms.CharField(
        label=_('Special Requests'),
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': _('Any special requests or requirements...')
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        pickup_date = cleaned_data.get('pickup_date')
        dropoff_date = cleaned_data.get('dropoff_date')
        
        # Validate dates
        if pickup_date and dropoff_date:
            if pickup_date < date.today():
                self.add_error('pickup_date', _('Pick-up date cannot be in the past.'))
            
            if dropoff_date <= pickup_date:
                self.add_error('dropoff_date', _('Drop-off date must be after pick-up date.'))
            
            # Validate maximum rental period (e.g., 90 days)
            max_rental_days = 90
            if (dropoff_date - pickup_date).days > max_rental_days:
                self.add_error('dropoff_date', 
                    _(f'Maximum rental period is {max_rental_days} days.'))
        
        # Set dropoff location to pickup location if empty
        dropoff_location = cleaned_data.get('dropoff_location')
        if not dropoff_location:
            cleaned_data['dropoff_location'] = cleaned_data.get('pickup_location')
        
        return cleaned_data


class CarReviewForm(forms.ModelForm):
    """Form for submitting car reviews."""
    
    class Meta:
        model = CarReview
        fields = ['rating', 'title', 'comment', 'cleanliness', 'comfort', 
                 'performance', 'fuel_efficiency', 'value_for_money']
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
            'performance': forms.Select(attrs={'class': 'form-control'}),
            'fuel_efficiency': forms.Select(attrs={'class': 'form-control'}),
            'value_for_money': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'rating': _('Overall Rating'),
            'cleanliness': _('Cleanliness'),
            'comfort': _('Comfort'),
            'performance': _('Performance'),
            'fuel_efficiency': _('Fuel Efficiency'),
            'value_for_money': _('Value for Money'),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set rating choices
        self.fields['rating'].choices = CarReview.Rating.choices
        for field in ['cleanliness', 'comfort', 'performance', 'fuel_efficiency', 'value_for_money']:
            self.fields[field].choices = [
                (i, '★' * i) for i in range(1, 6)
            ]


class CarAdminForm(forms.ModelForm):
    """Form for admin to manage cars."""
    
    class Meta:
        model = Car
        fields = '__all__'
        widgets = {
            'registration_number': forms.TextInput(attrs={'class': 'form-control'}),
            'brand': forms.Select(attrs={'class': 'form-control'}),
            'model': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'year': forms.NumberInput(attrs={'class': 'form-control'}),
            'color': forms.TextInput(attrs={'class': 'form-control'}),
            'transmission': forms.Select(attrs={'class': 'form-control'}),
            'fuel_type': forms.Select(attrs={'class': 'form-control'}),
            'engine_capacity': forms.NumberInput(attrs={'class': 'form-control'}),
            'mileage_kmpl': forms.NumberInput(attrs={'class': 'form-control'}),
            'seating_capacity': forms.NumberInput(attrs={'class': 'form-control'}),
            'baggage_capacity': forms.NumberInput(attrs={'class': 'form-control'}),
            'daily_rate': forms.NumberInput(attrs={'class': 'form-control'}),
            'weekly_rate': forms.NumberInput(attrs={'class': 'form-control'}),
            'monthly_rate': forms.NumberInput(attrs={'class': 'form-control'}),
            'security_deposit': forms.NumberInput(attrs={'class': 'form-control'}),
            'km_limit_per_day': forms.NumberInput(attrs={'class': 'form-control'}),
            'extra_km_charge': forms.NumberInput(attrs={'class': 'form-control'}),
            'pickup_location': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control'}),
            'insurance_number': forms.TextInput(attrs={'class': 'form-control'}),
            'insurance_valid_until': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'last_service_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'next_service_due': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }
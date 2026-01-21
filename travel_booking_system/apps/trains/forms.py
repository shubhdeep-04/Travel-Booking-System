"""
Forms for Train operations.
"""

from django import forms
from django.utils.translation import gettext_lazy as _
from datetime import date, timedelta

from .models import Train, TrainBooking, TrainReview, CoachType, TrainStop


class TrainSearchForm(forms.Form):
    """Form for searching trains."""
    from_station = forms.CharField(
        label=_('From Station'),
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter departure station'),
            'id': 'trainFrom'
        })
    )
    to_station = forms.CharField(
        label=_('To Station'),
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter destination station'),
            'id': 'trainTo'
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
    train_type = forms.ChoiceField(
        label=_('Train Type'),
        choices=[('', _('All Types'))] + list(Train.TrainType.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        from_station = cleaned_data.get('from_station')
        to_station = cleaned_data.get('to_station')
        travel_date = cleaned_data.get('travel_date')
        
        if from_station and to_station:
            if from_station.lower() == to_station.lower():
                raise forms.ValidationError(_('Departure and destination cannot be the same.'))
        
        if travel_date:
            if travel_date < date.today():
                raise forms.ValidationError(_('Travel date cannot be in the past.'))
            
            # Maximum advance booking (e.g., 120 days for trains)
            max_advance_days = 120
            if travel_date > date.today() + timedelta(days=max_advance_days):
                raise forms.ValidationError(
                    _(f'Maximum advance booking is {max_advance_days} days.')
                )
        
        return cleaned_data


class TrainBookingForm(forms.Form):
    """Form for booking train tickets."""
    train_id = forms.UUIDField(widget=forms.HiddenInput())
    from_station = forms.CharField(
        label=_('From Station'),
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Departure station')
        })
    )
    to_station = forms.CharField(
        label=_('To Station'),
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Destination station')
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
    coach_type = forms.ModelChoiceField(
        label=_('Coach Class'),
        queryset=CoachType.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    quota = forms.ChoiceField(
        label=_('Quota'),
        choices=TrainBooking.QuotaType.choices,
        initial='GENERAL',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    seats = forms.CharField(
        label=_('Selected Seats'),
        required=False,
        widget=forms.HiddenInput()
    )
    
    # Passenger Information
    passenger_name = forms.CharField(
        label=_('Passenger Name'),
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('As per ID proof')
        })
    )
    passenger_age = forms.IntegerField(
        label=_('Passenger Age'),
        min_value=1,
        max_value=120,
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
    passenger_id_type = forms.ChoiceField(
        label=_('ID Proof Type'),
        choices=[
            ('AADHAAR', 'Aadhaar'),
            ('PAN', 'PAN'),
            ('PASSPORT', 'Passport'),
            ('DRIVING_LICENSE', 'Driving License'),
            ('VOTER_ID', 'Voter ID'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    passenger_id_number = forms.CharField(
        label=_('ID Proof Number'),
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter ID number')
        })
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
    
    def clean(self):
        cleaned_data = super().clean()
        travel_date = cleaned_data.get('travel_date')
        from_station = cleaned_data.get('from_station')
        to_station = cleaned_data.get('to_station')
        
        # Validate travel date
        if travel_date:
            if travel_date < date.today():
                self.add_error('travel_date', _('Travel date cannot be in the past.'))
            
            # Check if date is too far in future
            max_advance_days = 120
            if travel_date > date.today() + timedelta(days=max_advance_days):
                self.add_error('travel_date', 
                    _(f'Maximum advance booking is {max_advance_days} days.'))
        
        # Validate stations
        if from_station and to_station:
            if from_station.lower() == to_station.lower():
                self.add_error('to_station', _('Destination must be different from departure.'))
        
        # Validate age for senior citizen quota
        quota = cleaned_data.get('quota')
        age = cleaned_data.get('passenger_age')
        if quota == 'SENIOR_CITIZEN' and age and age < 60:
            self.add_error('quota', _('Senior citizen quota is only for passengers aged 60 and above.'))
        
        return cleaned_data


class TrainReviewForm(forms.ModelForm):
    """Form for submitting train reviews."""
    
    class Meta:
        model = TrainReview
        fields = ['rating', 'title', 'comment', 'cleanliness', 'comfort', 
                 'punctuality', 'staff_behavior', 'food_quality', 'value_for_money']
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
            'food_quality': forms.Select(attrs={'class': 'form-control'}),
            'value_for_money': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'rating': _('Overall Rating'),
            'cleanliness': _('Cleanliness'),
            'comfort': _('Comfort'),
            'punctuality': _('Punctuality'),
            'staff_behavior': _('Staff Behavior'),
            'food_quality': _('Food Quality'),
            'value_for_money': _('Value for Money'),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set rating choices
        self.fields['rating'].choices = TrainReview.Rating.choices
        for field in ['cleanliness', 'comfort', 'punctuality', 'staff_behavior', 'food_quality', 'value_for_money']:
            self.fields[field].choices = [
                (i, '★' * i) for i in range(1, 6)
            ]


class TrainAdminForm(forms.ModelForm):
    """Form for admin to manage trains."""
    
    class Meta:
        model = Train
        fields = '__all__'
        widgets = {
            'train_number': forms.TextInput(attrs={'class': 'form-control'}),
            'train_name': forms.TextInput(attrs={'class': 'form-control'}),
            'train_type': forms.Select(attrs={'class': 'form-control'}),
            'source_station': forms.TextInput(attrs={'class': 'form-control'}),
            'destination_station': forms.TextInput(attrs={'class': 'form-control'}),
            'source_station_code': forms.TextInput(attrs={'class': 'form-control'}),
            'destination_station_code': forms.TextInput(attrs={'class': 'form-control'}),
            'departure_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'arrival_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'running_days': forms.TextInput(attrs={'class': 'form-control'}),
            'duration_hours': forms.NumberInput(attrs={'class': 'form-control'}),
            'distance_km': forms.NumberInput(attrs={'class': 'form-control'}),
            'total_coaches': forms.NumberInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
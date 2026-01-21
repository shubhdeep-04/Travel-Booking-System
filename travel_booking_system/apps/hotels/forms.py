"""
Forms for Hotel operations.
"""

from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import date, timedelta

from .models import Hotel, HotelRoom, HotelReview, RoomType


class HotelSearchForm(forms.Form):
    """Form for searching hotels."""
    city = forms.CharField(
        label=_('City'),
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter city name'),
            'id': 'hotelSearchCity'
        })
    )
    check_in = forms.DateField(
        label=_('Check-in'),
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'min': date.today().isoformat()
        })
    )
    check_out = forms.DateField(
        label=_('Check-out'),
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'min': (date.today() + timedelta(days=1)).isoformat()
        })
    )
    guests = forms.IntegerField(
        label=_('Guests'),
        required=False,
        initial=1,
        min_value=1,
        max_value=20,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1,
            'max': 20
        })
    )
    rooms = forms.IntegerField(
        label=_('Rooms'),
        required=False,
        initial=1,
        min_value=1,
        max_value=10,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1,
            'max': 10
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        check_in = cleaned_data.get('check_in')
        check_out = cleaned_data.get('check_out')
        
        if check_in and check_out:
            if check_in < date.today():
                raise forms.ValidationError(_('Check-in date cannot be in the past.'))
            if check_out <= check_in:
                raise forms.ValidationError(_('Check-out date must be after check-in date.'))
        
        return cleaned_data


class HotelBookingForm(forms.Form):
    """Form for booking a hotel room."""
    hotel_id = forms.UUIDField(widget=forms.HiddenInput())
    room_type_id = forms.UUIDField(widget=forms.HiddenInput())
    
    check_in = forms.DateField(
        label=_('Check-in Date'),
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'min': date.today().isoformat()
        })
    )
    check_out = forms.DateField(
        label=_('Check-out Date'),
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'min': (date.today() + timedelta(days=1)).isoformat()
        })
    )
    rooms = forms.IntegerField(
        label=_('Number of Rooms'),
        initial=1,
        min_value=1,
        max_value=10,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1,
            'max': 10
        })
    )
    guests = forms.IntegerField(
        label=_('Number of Guests'),
        initial=1,
        min_value=1,
        max_value=20,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1,
            'max': 20
        })
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
        check_in = cleaned_data.get('check_in')
        check_out = cleaned_data.get('check_out')
        rooms = cleaned_data.get('rooms', 1)
        guests = cleaned_data.get('guests', 1)
        
        # Validate dates
        if check_in and check_out:
            if check_in < date.today():
                self.add_error('check_in', _('Check-in date cannot be in the past.'))
            
            if check_out <= check_in:
                self.add_error('check_out', _('Check-out date must be after check-in date.'))
            
            # Validate maximum stay (e.g., 30 days)
            max_stay = timedelta(days=30)
            if check_out - check_in > max_stay:
                self.add_error('check_out', _('Maximum stay is 30 days.'))
        
        # Validate guests per room (assuming 2 guests per room as default max)
        max_guests_per_room = 4
        if rooms and guests:
            if guests > rooms * max_guests_per_room:
                self.add_error('guests', 
                    _(f'Maximum {max_guests_per_room} guests per room. You need more rooms.'))
        
        return cleaned_data


class HotelReviewForm(forms.ModelForm):
    """Form for submitting hotel reviews."""
    
    class Meta:
        model = HotelReview
        fields = ['rating', 'title', 'comment', 'cleanliness', 'comfort', 
                 'location', 'facilities', 'staff', 'value_for_money']
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
            'location': forms.Select(attrs={'class': 'form-control'}),
            'facilities': forms.Select(attrs={'class': 'form-control'}),
            'staff': forms.Select(attrs={'class': 'form-control'}),
            'value_for_money': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'rating': _('Overall Rating'),
            'cleanliness': _('Cleanliness'),
            'comfort': _('Comfort'),
            'location': _('Location'),
            'facilities': _('Facilities'),
            'staff': _('Staff'),
            'value_for_money': _('Value for Money'),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set rating choices
        self.fields['rating'].choices = HotelReview.Rating.choices
        for field in ['cleanliness', 'comfort', 'location', 'facilities', 'staff', 'value_for_money']:
            self.fields[field].choices = [
                (i, '★' * i) for i in range(1, 6)
            ]


class HotelAdminForm(forms.ModelForm):
    """Form for admin to manage hotels."""
    
    class Meta:
        model = Hotel
        fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control'}),
            'star_rating': forms.Select(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
        }


class HotelRoomAdminForm(forms.ModelForm):
    """Form for admin to manage hotel rooms."""
    
    class Meta:
        model = HotelRoom
        fields = '__all__'
        widgets = {
            'hotel': forms.Select(attrs={'class': 'form-control'}),
            'room_type': forms.Select(attrs={'class': 'form-control'}),
            'room_number': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'size_sqft': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_guests': forms.NumberInput(attrs={'class': 'form-control'}),
            'bed_count': forms.NumberInput(attrs={'class': 'form-control'}),
            'bed_type': forms.Select(attrs={'class': 'form-control'}),
            'base_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'tax_percentage': forms.NumberInput(attrs={'class': 'form-control'}),
            'total_rooms': forms.NumberInput(attrs={'class': 'form-control'}),
            'available_rooms': forms.NumberInput(attrs={'class': 'form-control'}),
            'cancellation_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'cancellation_fee_percentage': forms.NumberInput(attrs={'class': 'form-control'}),
        }
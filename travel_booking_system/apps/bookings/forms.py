"""
Forms for Booking operations.
"""

from django import forms
from django.utils.translation import gettext_lazy as _
from datetime import date, timedelta

from .models import Booking


class BookingFilterForm(forms.Form):
    """Form for filtering bookings."""
    status = forms.ChoiceField(
        label=_('Status'),
        choices=[('all', _('All Status'))] + list(Booking.Status.choices),
        required=False,
        initial='all',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    service_type = forms.ChoiceField(
        label=_('Service Type'),
        choices=[('all', _('All Services'))] + list(Booking.ServiceType.choices),
        required=False,
        initial='all',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    date_from = forms.DateField(
        label=_('From Date'),
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    date_to = forms.DateField(
        label=_('To Date'),
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to:
            if date_to < date_from:
                raise forms.ValidationError(_('To date must be after from date.'))
        
        return cleaned_data


class CancelBookingForm(forms.Form):
    """Form for cancelling a booking."""
    booking_id = forms.UUIDField(widget=forms.HiddenInput())
    reason = forms.CharField(
        label=_('Cancellation Reason'),
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': _('Please provide a reason for cancellation...')
        })
    )
    refund_preference = forms.ChoiceField(
        label=_('Refund Preference'),
        choices=[
            ('WALLET', _('Credit to Wallet')),
            ('BANK', _('Bank Transfer')),
            ('CARD', _('Original Payment Method')),
        ],
        required=False,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    def clean_reason(self):
        reason = self.cleaned_data.get('reason', '').strip()
        if len(reason) < 10:
            raise forms.ValidationError(_('Please provide a detailed reason (minimum 10 characters).'))
        return reason


class BookingAdminForm(forms.ModelForm):
    """Form for admin to manage bookings."""
    
    class Meta:
        model = Booking
        fields = '__all__'
        widgets = {
            'user': forms.Select(attrs={'class': 'form-control'}),
            'service_type': forms.Select(attrs={'class': 'form-control'}),
            'service_id': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'check_in_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'check_out_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'travel_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'adults': forms.NumberInput(attrs={'class': 'form-control'}),
            'children': forms.NumberInput(attrs={'class': 'form-control'}),
            'base_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'tax_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'discount_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'total_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'special_requests': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'cancellation_reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'refund_amount': forms.NumberInput(attrs={'class': 'form-control'}),
        }
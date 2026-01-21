"""
Forms for Payment operations.
"""

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Payment, Refund


class PaymentForm(forms.ModelForm):
    """Form for making a payment."""
    
    class Meta:
        model = Payment
        fields = ['payment_method', 'payment_gateway', 'card_last4']
        widgets = {
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'payment_gateway': forms.Select(attrs={'class': 'form-control'}),
            'card_last4': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last 4 digits',
                'maxlength': 4
            }),
        }
    
    booking = forms.ModelChoiceField(
        queryset=None,
        widget=forms.HiddenInput()
    )
    amount = forms.DecimalField(
        label=_('Amount'),
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly'
        })
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            from apps.bookings.models import Booking
            self.fields['booking'].queryset = Booking.objects.filter(
                user=user,
                status='PENDING'
            )
        
        # Set payment method choices
        self.fields['payment_method'].choices = Payment.PaymentMethod.choices
        
        # Add card details fields if credit/debit card selected
        self.fields['card_number'] = forms.CharField(
            required=False,
            widget=forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Card number',
                'data-mask': '0000 0000 0000 0000'
            })
        )
        self.fields['expiry_date'] = forms.CharField(
            required=False,
            widget=forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'MM/YY',
                'data-mask': '00/00'
            })
        )
        self.fields['cvv'] = forms.CharField(
            required=False,
            widget=forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'CVV',
                'maxlength': 4
            })
        )
        
        # Add UPI field if UPI selected
        self.fields['upi_id'] = forms.CharField(
            required=False,
            widget=forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'UPI ID (e.g., user@upi)'
            })
        )
    
    def clean(self):
        cleaned_data = super().clean()
        payment_method = cleaned_data.get('payment_method')
        
        # Validate card details for card payments
        if payment_method in ['CREDIT_CARD', 'DEBIT_CARD']:
            card_number = cleaned_data.get('card_number', '').replace(' ', '')
            expiry_date = cleaned_data.get('expiry_date', '')
            cvv = cleaned_data.get('cvv', '')
            
            if not card_number or not expiry_date or not cvv:
                raise forms.ValidationError(
                    _('Card number, expiry date, and CVV are required for card payments.')
                )
            
            # Validate expiry date format
            if '/' not in expiry_date:
                raise forms.ValidationError(
                    _('Expiry date must be in MM/YY format.')
                )
            
            try:
                month, year = expiry_date.split('/')
                month = int(month)
                year = int(year) + 2000  # Convert YY to YYYY
                
                from datetime import date
                if month < 1 or month > 12:
                    raise forms.ValidationError(_('Invalid month.'))
                
                current_year = date.today().year
                current_month = date.today().month
                
                if year < current_year or (year == current_year and month < current_month):
                    raise forms.ValidationError(_('Card has expired.'))
                
            except (ValueError, IndexError):
                raise forms.ValidationError(_('Invalid expiry date format.'))
        
        # Validate UPI ID for UPI payments
        elif payment_method == 'UPI':
            upi_id = cleaned_data.get('upi_id', '')
            if not upi_id:
                raise forms.ValidationError(_('UPI ID is required for UPI payments.'))
            if '@' not in upi_id:
                raise forms.ValidationError(_('Invalid UPI ID format.'))
        
        return cleaned_data


class RefundRequestForm(forms.ModelForm):
    """Form for requesting a refund."""
    
    class Meta:
        model = Refund
        fields = ['refund_method', 'reason']
        widgets = {
            'refund_method': forms.Select(attrs={'class': 'form-control'}),
            'reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _('Please provide a detailed reason for the refund...')
            }),
        }
    
    payment = forms.ModelChoiceField(
        queryset=None,
        widget=forms.HiddenInput()
    )
    amount = forms.DecimalField(
        label=_('Refund Amount'),
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            from .models import Payment
            self.fields['payment'].queryset = Payment.objects.filter(
                booking__user=user,
                status='COMPLETED'
            )
        
        # Set refund method choices
        self.fields['refund_method'].choices = Refund.RefundMethod.choices
    
    def clean(self):
        cleaned_data = super().clean()
        payment = cleaned_data.get('payment')
        amount = cleaned_data.get('amount')
        
        if payment and amount:
            if amount > payment.amount:
                raise forms.ValidationError(
                    _('Refund amount cannot exceed the original payment amount.')
                )
        
        return cleaned_data


class WalletTopupForm(forms.Form):
    """Form for adding credit to wallet."""
    amount = forms.DecimalField(
        label=_('Amount'),
        max_digits=12,
        decimal_places=2,
        min_value=10.00,  # Minimum top-up amount
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Minimum $10.00'
        })
    )
    payment_method = forms.ChoiceField(
        label=_('Payment Method'),
        choices=[
            ('CREDIT_CARD', 'Credit Card'),
            ('DEBIT_CARD', 'Debit Card'),
            ('UPI', 'UPI'),
            ('NET_BANKING', 'Net Banking'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount < 10:
            raise forms.ValidationError(_('Minimum top-up amount is $10.00'))
        return amount


class PaymentFilterForm(forms.Form):
    """Form for filtering payments."""
    status = forms.ChoiceField(
        label=_('Status'),
        choices=[('all', _('All Status'))] + list(Payment.PaymentStatus.choices),
        required=False,
        initial='all',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    payment_method = forms.ChoiceField(
        label=_('Payment Method'),
        choices=[('all', _('All Methods'))] + list(Payment.PaymentMethod.choices),
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
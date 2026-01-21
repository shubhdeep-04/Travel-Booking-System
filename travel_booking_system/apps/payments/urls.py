"""
URL configuration for payments app.
"""

from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # Payment views
    path('create/', views.CreatePaymentView.as_view(), name='create_payment'),
    path('<uuid:pk>/', views.PaymentDetailView.as_view(), name='payment_detail'),
    path('my-payments/', views.MyPaymentsView.as_view(), name='my_payments'),
    path('<uuid:pk>/invoice/', views.PaymentInvoiceView.as_view(), name='payment_invoice'),
    
    # Wallet views
    path('wallet/', views.wallet_view, name='wallet'),
    path('wallet/add-credit/', views.add_wallet_credit, name='add_wallet_credit'),
    
    # Refund views
    path('refund/request/<uuid:payment_id>/', views.RequestRefundView.as_view(), name='request_refund'),
    path('refunds/', views.MyRefundsView.as_view(), name='my_refunds'),
    
    # Webhook
    path('webhook/', views.payment_webhook, name='payment_webhook'),
    
    # Admin views
    path('admin/list/', views.AdminPaymentListView.as_view(), name='admin_payment_list'),
]
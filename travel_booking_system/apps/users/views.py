"""
Views for User authentication and management.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, UpdateView, DetailView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.decorators.http import require_http_methods
from django.views.generic import ListView

from .forms import (
    CustomUserCreationForm,
    LoginForm,
    ProfileUpdateForm,
    PasswordChangeCustomForm
)
from .models import User, UserProfile

class SignUpView(CreateView):
    """View for user registration."""
    form_class = CustomUserCreationForm
    template_name = 'users/signup.html'
    success_url = reverse_lazy('login')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            _('Account created successfully! You can now log in.')
        )
        return response


@require_http_methods(["GET", "POST"])
def login_view(request):
    """Handle user login."""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            remember_me = form.cleaned_data.get('remember_me')
            
            # Try to authenticate with username or email
            user = authenticate(
                request,
                username=username,
                password=password
            )
            
            # If authentication with username fails, try with email
            if user is None:
                try:
                    user_obj = User.objects.get(email=username)
                    user = authenticate(
                        request,
                        username=user_obj.username,
                        password=password
                    )
                except User.DoesNotExist:
                    user = None
            
            if user is not None:
                login(request, user)
                
                # Handle remember me
                if not remember_me:
                    request.session.set_expiry(0)  # Session expires on browser close
                
                messages.success(request, _('Logged in successfully!'))
                
                # Redirect to next parameter or home
                next_url = request.GET.get('next', 'home')
                return redirect(next_url)
            else:
                messages.error(request, _('Invalid username/email or password.'))
    else:
        form = LoginForm()
    
    return render(request, 'users/login.html', {'form': form})


@login_required
def logout_view(request):
    """Handle user logout."""
    logout(request)
    messages.success(request, _('Logged out successfully!'))
    return redirect('home')


class ProfileView(LoginRequiredMixin, DetailView):
    """View user profile."""
    model = User
    template_name = 'users/profile.html'
    context_object_name = 'user_obj'
    
    def get_object(self):
        return self.request.user


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """Update user profile."""
    model = User
    form_class = ProfileUpdateForm
    template_name = 'users/profile_update.html'
    success_url = reverse_lazy('profile')
    
    def get_object(self):
        return self.request.user
    
    def form_valid(self, form):
        messages.success(self.request, _('Profile updated successfully!'))
        return super().form_valid(form)


@login_required
def change_password_view(request):
    """Handle password change."""
    if request.method == 'POST':
        form = PasswordChangeCustomForm(request.POST)
        if form.is_valid():
            current_password = form.cleaned_data.get('current_password')
            new_password = form.cleaned_data.get('new_password')
            
            # Check current password
            if not request.user.check_password(current_password):
                messages.error(request, _('Current password is incorrect.'))
                return render(request, 'users/change_password.html', {'form': form})
            
            # Change password
            request.user.set_password(new_password)
            request.user.save()
            
            # Update session to prevent logout
            update_session_auth_hash(request, request.user)
            
            messages.success(request, _('Password changed successfully!'))
            return redirect('profile')
    else:
        form = PasswordChangeCustomForm()
    
    return render(request, 'users/change_password.html', {'form': form})


@login_required
def delete_account_view(request):
    """Handle account deletion."""
    if request.method == 'POST':
        user = request.user
        logout(request)
        user.delete()
        messages.success(request, _('Your account has been deleted.'))
        return redirect('home')
    
    return render(request, 'users/delete_account.html')


class AdminOnlyMixin(UserPassesTestMixin):
    """Mixin to restrict access to admin users only."""
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_admin


class UserListView(AdminOnlyMixin, ListView):
    """List all users (admin only)."""
    model = User
    template_name = 'users/user_list.html'
    context_object_name = 'users'
    paginate_by = 20
    
    def get_queryset(self):
        return User.objects.all().order_by('-date_joined')


class UserDetailView(AdminOnlyMixin, DetailView):
    """View user details (admin only)."""
    model = User
    template_name = 'users/user_detail_admin.html'
    context_object_name = 'user_obj'


@login_required
def dashboard_view(request):
    """User dashboard with recent bookings and stats."""
    # Import here to avoid circular imports
    from apps.bookings.models import Booking
    
    recent_bookings = Booking.objects.filter(user=request.user)[:5]
    
    context = {
        'recent_bookings': recent_bookings,
        'total_bookings': Booking.objects.filter(user=request.user).count(),
    }
    
    return render(request, 'users/dashboard.html', context)
"""
Admin configuration for User model.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, UserProfile
from .forms import CustomUserCreationForm, CustomUserChangeForm

class UserProfileInline(admin.StackedInline):
    """Inline admin for UserProfile."""
    model = UserProfile
    can_delete = False
    verbose_name_plural = _('Profile')
    fk_name = 'user'
    fields = ('loyalty_points', 'newsletter_subscription', 'preferences')
    readonly_fields = ('loyalty_points',)

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for User model."""
    
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    inlines = (UserProfileInline,)
    
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_active', 'date_joined')
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal Info'), {
            'fields': (
                'first_name', 'last_name', 'email', 'phone',
                'date_of_birth', 'profile_image'
            )
        }),
        (_('Location'), {
            'fields': ('address', 'city', 'country', 'postal_code'),
            'classes': ('collapse',)
        }),
        (_('Permissions'), {
            'fields': (
                'role', 'is_active', 'is_staff', 'is_superuser',
                'is_verified', 'groups', 'user_permissions'
            ),
            'classes': ('collapse',)
        }),
        (_('Important dates'), {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username', 'email', 'first_name', 'last_name',
                'phone', 'password1', 'password2', 'role'
            ),
        }),
    )
    
    filter_horizontal = ('groups', 'user_permissions')
    
    def get_inline_instances(self, request, obj=None):
        """Only show inline if editing existing user."""
        if not obj:
            return []
        return super().get_inline_instances(request, obj)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin configuration for UserProfile."""
    
    list_display = ('user', 'loyalty_points', 'newsletter_subscription')
    list_filter = ('newsletter_subscription',)
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('user', 'loyalty_points')
    
    fieldsets = (
        (None, {'fields': ('user',)}),
        (_('Preferences'), {
            'fields': ('preferences', 'newsletter_subscription')
        }),
        (_('Terms & Conditions'), {
            'fields': ('terms_accepted', 'privacy_policy_accepted')
        }),
        (_('Loyalty'), {
            'fields': ('loyalty_points',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Prevent adding profiles directly."""
        return False
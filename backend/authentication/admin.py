from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, MedicalHistory


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for custom User model"""
    
    list_display = ['email', 'name', 'is_email_verified', 'is_staff', 'created_at']
    list_filter = ['is_email_verified', 'is_staff', 'is_superuser', 'gender', 'created_at']
    search_fields = ['email', 'name']
    ordering = ['-created_at']
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('name', 'age', 'gender')}),
        ('Email Verification', {
            'fields': (
                'is_email_verified', 
                'email_verification_otp', 
                'email_verification_sent_at',
                'email_verification_attempts'
            )
        }),
        ('Password Reset', {
            'fields': (
                'password_reset_otp',
                'password_reset_sent_at',
                'password_reset_attempts'
            )
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Important Dates', {'fields': ('last_login_at', 'created_at', 'updated_at')}),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'name', 'password1', 'password2'),
        }),
    )


@admin.register(MedicalHistory)
class MedicalHistoryAdmin(admin.ModelAdmin):
    """Admin configuration for Medical History model"""
    
    list_display = ['user', 'created_at', 'updated_at']
    search_fields = ['user__email', 'user__name', 'medical_notes']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {'fields': ('user', 'medical_notes')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )

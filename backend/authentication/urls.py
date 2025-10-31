from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

app_name = 'authentication'

urlpatterns = [
    # Authentication endpoints
    path('register/', views.register, name='register'),
    path('verify-email/', views.verify_email, name='verify_email'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Password reset endpoints
    path('password-reset/request/', views.password_reset_request, name='password_reset_request'),
    path('password-reset/confirm/', views.password_reset_confirm, name='password_reset_confirm'),
    
    # Resend verification
    path('resend-verification/', views.resend_verification, name='resend_verification'),
    
    # User profile endpoints
    path('user/profile/', views.get_user_profile, name='get_user_profile'),
    path('user/profile/', views.update_user_profile, name='update_user_profile'),
    path('user/change-password/', views.change_password, name='change_password'),
    
    # Medical history endpoints
    path('user/medical-history/', views.create_or_update_medical_history, name='create_or_update_medical_history'),
    path('user/medical-history/', views.get_medical_history, name='get_medical_history'),
]

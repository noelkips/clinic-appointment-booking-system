from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import include, path
from clinic import views
from .health import health

urlpatterns = [
    path('health/', health, name='health'),
    path('django-admin/', admin.site.urls),
    path('accounts/login/', views.SignInView.as_view(), name='login'),
    path('accounts/logout/', LogoutView.as_view(), name='logout'),
    path('accounts/register/', views.RegisterView.as_view(), name='register'),
    path('accounts/forgot-password/', views.forgot_password, name='forgot-password'),
    path('api/', include('clinic.api_urls')),
    path('', include('clinic.urls')),
]

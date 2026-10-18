from django.contrib import admin
from django.urls import include, path
from clinic.views import RegisterView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/register/', RegisterView.as_view(), name='register'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('api/', include('clinic.api_urls')),
    path('', include('clinic.urls')),
]

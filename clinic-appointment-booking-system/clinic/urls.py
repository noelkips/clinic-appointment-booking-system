from django.urls import path
from .views import book, dashboard
urlpatterns = [path('', dashboard, name='dashboard'), path('appointments/book/', book, name='book')]

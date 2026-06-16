from django.contrib import admin
from django.urls import path, include
from main import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.onboarding, name='onboarding'),
    path('signup_login/', views.signup_login, name='signup_login'),
    
    path('accounts/', include('accounts.urls')), 
]
from django.urls import path

from .views import *

app_name = 'main'

urlpatterns = [
    path('', onboarding, name='onboarding'),
    path('signup_login/', signup_login, name='signup_login'),
    path('dashboard/', dashboard, name='dashboard'),

    path('join_pot/', join_pot, name='join_pot'),
    path('new_pot/', new_pot, name='new_pot'), 
    path('create_pot/', create_pot, name='create_pot'),
]
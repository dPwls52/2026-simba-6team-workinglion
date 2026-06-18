from django.urls import path

from .views import *

app_name = 'main'

urlpatterns = [
    path('', onboarding, name='onboarding'),
    path('signup_login/', signup_login, name='signup_login'),
    path('dashboard/', dashboard, name='dashboard'),
    path('pot_choice/', pot_choice, name='pot_choice'),
    path('join_pot/<int:pot_id>', join_pot, name='join_pot'),
    path('new_pot/', new_pot, name='new_pot'), 
    path('create/', create, name='create'),
]
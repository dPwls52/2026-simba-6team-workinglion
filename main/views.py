from django.shortcuts import render, redirect, get_object_or_404
from .models import *

# Create your views here.
def onboarding(request):
    return render(request, 'pages/onboarding.html')

def signup_login(request):
    return render(request, 'pages/signup_login.html')

def dashboard(request):
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    pots = Pot.objects.all()
    return render(request, 'pages/dashboard.html', {'pots': pots})

def pot_choice(request):
    return render(request, 'pages/pot-choice.html')

def join_pot(request, pot_id):
    pot = get_object_or_404(Pot, pk=pot_id)
    return render(request, 'pages/join_pot.html', {'pot': pot})

def join_pot_action(request, pot_id):
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    pot = get_object_or_404(Pot, pk=pot_id)

    if request.user in pot.participants.all():
        pot.participants.remove(request.user)
    else:
        pot.participants.add(redquest.user)
    return redirect('main:dashboard')

def new_pot(request):
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    
    user_profile = request.user.profile
    return render(request, 'pages/new_pot.html', {'user_profile': user_profile})


def create(request):
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    new_pot = Pot()

    new_pot.pot_name = request.POST['pot-name']
    new_pot.host = request.user
    days = int(request.POST['challenge_term'])
    pot_people = int(request.POST['people'])

    new_pot.days = days
    new_pot.pot_people = pot_people
    fee = days * 100
    new_pot.fee = fee
    new_pot.total_prize = (fee * pot_people) + 500

    new_pot.save()

    return redirect('main:dashboard')

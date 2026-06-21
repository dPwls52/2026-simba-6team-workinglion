from django.shortcuts import render, redirect, get_object_or_404
from .models import *
import datetime
import random
import string

# Create your views here.
def onboarding(request):
    return render(request, 'pages/onboarding.html')

def signup_login(request):
    return render(request, 'pages/signup_login.html')

def dashboard(request):
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    pots = Pot.objects.filter(participants=request.user)
    return render(request, 'pages/dashboard.html', {'pots': pots})


def pot_detail(request, pot_id):
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    pot = get_object_or_404(Pot, pk=pot_id)

    if not pot.participants.filter(id=request.user.id).exists():
        return redirect('main:dashboard')

    today = datetime.date.today()

    if request.method == 'POST':
        image = request.FILES.get('image')
        if image:
            if not Proof.objects.filter(
                pot=pot,
                user=request.user,
                auth_date=today,
            ).exists():
                proof = Proof(
                    pot=pot,
                    user=request.user,
                    image=image,
                )
                proof.save()
        return redirect('main:pot_detail', pot_id=pot.id)

    participants = pot.participants.all()
    participant_infos = []
    my_today_proof = None

    for participant in participants:
        proof = None
        avatar_color = None
        if Proof.objects.filter(
            pot=pot,
            user=participant,
            auth_date=today,
        ).exists():
            proof = Proof.objects.get(
                pot=pot,
                user=participant,
                auth_date=today,
            )

        if PotAvatar.objects.filter(pot=pot, user=participant).exists():
            avatar = PotAvatar.objects.get(pot=pot, user=participant)
            avatar_color = avatar.color

        if participant == request.user:
            my_today_proof = proof

        participant_infos.append({
            'user': participant,
            'proof': proof,
            'avatar_color': avatar_color,
        })

    context = {
        'pot': pot,
        'participants': participants,
        'participant_infos': participant_infos,
        'my_today_proof': my_today_proof,
    }
    return render(request, 'pages/pot_detail.html', context)

def pot_choice(request):
    return render(request, 'pages/pot-choice.html')

def join_pot(request, pot_id=None):
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    if pot_id:
        pot = get_object_or_404(Pot, pk=pot_id)
        return render(request, 'pages/join_pot.html', {'pot': pot})

    return render(request, 'pages/join_pot.html')

def join_pot_action(request, pot_id=None):
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    if request.method != "POST":
        return redirect('main:join_pot')

    input_code = request.POST.get('entry_code')

    if pot_id:
        pot = get_object_or_404(Pot, pk=pot_id)
    else:
        if not Pot.objects.filter(pot_code=input_code).exists():
            return redirect('main:join_pot')
        pot = Pot.objects.get(pot_code=input_code)

    user = request.user

    if pot.participants.filter(id=user.id).exists():
        return redirect('main:dashboard')

    if pot.participants.count() >= pot.pot_people:
        return redirect('main:dashboard')

    user_profile = request.user.profile
    if input_code == pot.pot_code and user_profile.point >= pot.fee:
        pot.participants.add(user)
        user_profile.point -= pot.fee
        user_profile.save()
        return redirect('main:avatar_setting', pot_id=pot.id)
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

    string_pool = string.ascii_uppercase + string.digits 
    result = ""
    for i in range(6): 
        result += random.choice(string_pool) 
        
    new_pot.pot_code = result
    new_pot.save()

    new_pot.participants.add(request.user)

    return redirect('main:avatar_setting', pot_id=new_pot.id)

def avatar_setting(request, pot_id):
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    pot = get_object_or_404(Pot, pk=pot_id)

    if not pot.participants.filter(id=request.user.id).exists():
        return redirect('main:dashboard')

    selected_color = None
    my_avatar = None

    if PotAvatar.objects.filter(pot=pot, user=request.user).exists():
        my_avatar = PotAvatar.objects.get(pot=pot, user=request.user)
        selected_color = my_avatar.color

    used_colors = []
    avatars = PotAvatar.objects.filter(pot=pot)
    for avatar in avatars:
        if avatar.user != request.user:
            used_colors.append(avatar.color)

    error = None

    if request.method == 'POST':
        color = request.POST.get('color')
        colors = ['blue', 'purple', 'green', 'red', 'gray', 'pink']

        if not color or color not in colors:
            error = '색상을 선택해주세요.'
        elif PotAvatar.objects.filter(pot=pot, color=color).exists() and color != selected_color:
            error = '이미 다른 참가자가 선택한 색상입니다.'
        else:
            if my_avatar:
                my_avatar.color = color
                my_avatar.save()
            else:
                avatar = PotAvatar(
                    pot=pot,
                    user=request.user,
                    color=color,
                )
                avatar.save()
            return redirect('main:pot_detail', pot_id=pot.id)

    context = {
        'pot': pot,
        'selected_color': selected_color,
        'used_colors': used_colors,
        'error': error,
    }
    return render(request, 'pages/avatar_setting.html', context)

def before_photo(request, pot_id):
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    pot = get_object_or_404(Pot, pk=pot_id)

    if not pot.participants.filter(id=request.user.id).exists():
        return redirect('main:dashboard')

    today = datetime.date.today()
    my_today_proof = None

    if Proof.objects.filter(
        pot=pot,
        user=request.user,
        auth_date=today,
    ).exists():
        my_today_proof = Proof.objects.get(
            pot=pot,
            user=request.user,
            auth_date=today,
        )

    if request.method == 'POST':
        if my_today_proof:
            return redirect('main:pot_detail', pot_id=pot.id)

        image = request.FILES.get('image')
        if image:
            proof = Proof(
                pot=pot,
                user=request.user,
                image=image,
            )
            proof.save()
            return redirect('main:pot_detail', pot_id=pot.id)

        context = {
            'pot': pot,
            'now': today,
            'my_today_proof': my_today_proof,
            'error': '인증사진을 선택해주세요.',
        }
        return render(request, 'pages/before_photo.html', context)

    context = {
        'pot': pot,
        'now': today,
        'my_today_proof': my_today_proof,
    }
    return render(request, 'pages/before_photo.html', context)

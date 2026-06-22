from django.shortcuts import render, redirect, get_object_or_404
from .models import *
import datetime
import random
import string

DAY_CODES = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']


def get_auth_days(pot):
    auth_days = pot.auth_days.split(',')
    selected_days = []
    for day in auth_days:
        if day in DAY_CODES:
            selected_days.append(day)
    return selected_days


def get_end_date(pot):
    return pot.start_date + datetime.timedelta(days=pot.days - 1)


def is_pot_ended(pot, today):
    return today > get_end_date(pot)


def is_auth_day(pot, today):
    return DAY_CODES[today.weekday()] in get_auth_days(pot)


def get_required_auth_count(pot):
    required_count = 0
    selected_days = get_auth_days(pot)
    check_date = pot.start_date
    end_date = get_end_date(pot)

    while check_date <= end_date:
        if DAY_CODES[check_date.weekday()] in selected_days:
            required_count += 1
        check_date += datetime.timedelta(days=1)

    return required_count


def get_valid_proof_count(pot, user):
    valid_count = 0
    selected_days = get_auth_days(pot)
    end_date = get_end_date(pot)
    proofs = Proof.objects.filter(pot=pot, user=user, is_valid=True)

    for proof in proofs:
        if pot.start_date <= proof.auth_date <= end_date:
            if DAY_CODES[proof.auth_date.weekday()] in selected_days:
                valid_count += 1

    return valid_count


# Create your views here.
def onboarding(request):
    return render(request, 'pages/onboarding.html')

def signup_login(request):
    return render(request, 'pages/signup_login.html')

def dashboard(request):
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    today = datetime.date.today()
    pots = Pot.objects.filter(participants=request.user)
    for pot in pots:
        pot.d_day = max((get_end_date(pot) - today).days, 0)
        pot.is_ended = is_pot_ended(pot, today)
        pot.is_authenticated_today = Proof.objects.filter(pot=pot, user=request.user, auth_date=today).exists()
    empty_slots = range(max(0, 4 - len(pots))) 
    
    return render(request, 'pages/dashboard.html', {
        'pots': pots,
        'empty_slots': empty_slots
    })

    return render(request, 'pages/dashboard.html', {'pots': pots})
def pot_detail(request, pot_id):
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    pot = get_object_or_404(Pot, pk=pot_id)

    if not pot.participants.filter(id=request.user.id).exists():
        return redirect('main:dashboard')

    today = datetime.date.today()
    if is_pot_ended(pot, today):
        return redirect('main:complete', pot_id=pot.id)

    d_day = max((get_end_date(pot) - today).days, 0)

    if request.method == 'POST':
        treat_item = request.POST.get('treat-item')
        target_user_id = request.POST.get('select-people', '')
        prices = {'post': 50, 'poop': 100, 'glasses': 70, 'flower': 70, 'gyaru': 120}

        if treat_item not in prices or not target_user_id.isdigit():
            return redirect('main:pot_detail', pot_id=pot.id)

        if str(request.user.id) == target_user_id:
            return redirect('main:pot_detail', pot_id=pot.id)

        if not pot.participants.filter(id=target_user_id).exists():
            return redirect('main:pot_detail', pot_id=pot.id)

        target_user = get_object_or_404(User, pk=target_user_id)
        if not PotAvatar.objects.filter(pot=pot, user=target_user).exists():
            return redirect('main:pot_detail', pot_id=pot.id)

        price = prices[treat_item]
        my_profile = request.user.profile
        if my_profile.point >= price:
            my_profile.point -= price
            my_profile.save()

            target_avatar = PotAvatar.objects.get(pot=pot, user=target_user)
            target_avatar.item = treat_item
            target_avatar.item_applied_at = datetime.datetime.now(datetime.timezone.utc)
            target_avatar.save()

        return redirect('main:pot_detail', pot_id=pot.id)

    participants = pot.participants.all()
    participant_infos = []
    my_today_proof = None
    now = datetime.datetime.now(datetime.timezone.utc)

    for participant in participants:
        proof = None
        vote_proof = None
        avatar_color = None
        avatar_item = None

        if Proof.objects.filter(pot=pot, user=participant, auth_date=today).exists():
            vote_proof = Proof.objects.get(pot=pot, user=participant, auth_date=today)
            if vote_proof.is_valid:
                proof = vote_proof

        if PotAvatar.objects.filter(pot=pot, user=participant).exists():
            avatar = PotAvatar.objects.get(pot=pot, user=participant)
            avatar_color = avatar.color

            if avatar.item and avatar.item_applied_at:
                expires_at = avatar.item_applied_at + datetime.timedelta(hours=48)
                if now < expires_at:
                    avatar_item = avatar.item
                else:
                    avatar.item = None
                    avatar.item_applied_at = None
                    avatar.save()

        if participant == request.user:
            my_today_proof = proof

        participant_infos.append({
            'user': participant,
            'proof': proof,
            'vote_proof': vote_proof,
            'avatar_color': avatar_color,
            'avatar_item': avatar_item,
        })

    context = {
        'pot': pot,
        'participants': participants,
        'participant_infos': participant_infos,
        'my_today_proof': my_today_proof,
        'd_day': d_day,
        'can_authenticate_today': is_auth_day(pot, today),
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

    if request.method != 'POST':
        return redirect('main:join_pot')

    input_code = request.POST.get('entry_code', '').strip().upper()

    if not input_code:
        return render(request, 'pages/join_pot.html', {'error': '입장코드를 입력해주세요.'})

    if pot_id:
        pot = get_object_or_404(Pot, pk=pot_id)
    else:
        if not Pot.objects.filter(pot_code=input_code).exists():
            return render(request, 'pages/join_pot.html', {'error': '존재하지 않는 입장코드입니다.'})
        pot = Pot.objects.get(pot_code=input_code)

    if input_code != pot.pot_code:
        return render(request, 'pages/join_pot.html', {'error': '입장코드가 일치하지 않습니다.'})

    today = datetime.date.today()
    if today > pot.start_date:
        return render(request, 'pages/join_pot.html', {'error': '참여 기간이 종료된 팟입니다.'})

    user = request.user
    if pot.participants.filter(id=user.id).exists():
        return render(request, 'pages/join_pot.html', {'error': '이미 참여 중인 팟입니다.'})

    if pot.participants.count() >= pot.pot_people:
        return render(request, 'pages/join_pot.html', {'error': '팟 정원이 모두 찼습니다.'})

    user_profile = request.user.profile
    if user_profile.point < pot.fee:
        return render(request, 'pages/join_pot.html', {'error': '포인트가 부족합니다.'})

    pot.participants.add(user)
    user_profile.point -= pot.fee
    user_profile.save()

    pot.total_prize = (pot.fee * pot.participants.count()) + 500
    pot.save()

    return redirect('main:avatar_setting', pot_id=pot.id)
def new_pot(request):
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    
    user_profile = request.user.profile
    return render(request, 'pages/new_pot.html', {'user_profile': user_profile})


def create(request):
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    if request.method != 'POST':
        return redirect('main:new_pot')

    pot_name = request.POST.get('pot-name', '').strip()
    challenge_term = request.POST.get('challenge_term')
    people = request.POST.get('people')
    user_profile = request.user.profile

    selected_days = []
    for day in DAY_CODES:
        if request.POST.get('auth_' + day):
            selected_days.append(day)

    if not pot_name:
        return render(request, 'pages/new_pot.html', {'user_profile': user_profile, 'error': '팟 이름을 입력해주세요.'})

    if len(pot_name) > 100:
        return render(request, 'pages/new_pot.html', {'user_profile': user_profile, 'error': '팟 이름은 100자 이하로 입력해주세요.'})

    if challenge_term not in ['7', '14', '30']:
        return render(request, 'pages/new_pot.html', {'user_profile': user_profile, 'error': '챌린지 기간을 선택해주세요.'})

    if not selected_days:
        return render(request, 'pages/new_pot.html', {'user_profile': user_profile, 'error': '인증 요일을 선택해주세요.'})

    if people not in ['2', '3', '4', '5', '6']:
        return render(request, 'pages/new_pot.html', {'user_profile': user_profile, 'error': '팟 인원을 선택해주세요.'})

    days = int(challenge_term)
    pot_people = int(people)
    fee = days * 100

    if user_profile.point < fee:
        return render(request, 'pages/new_pot.html', {'user_profile': user_profile, 'error': '포인트가 부족합니다.'})

    new_pot = Pot(
        pot_name=pot_name,
        host=request.user,
        days=days,
        auth_days=','.join(selected_days),
        pot_people=pot_people,
        fee=fee,
        total_prize=fee + 500,
    )

    string_pool = string.ascii_uppercase + string.digits
    while True:
        result = ''
        for i in range(6):
            result += random.choice(string_pool)
        if not Pot.objects.filter(pot_code=result).exists():
            break

    new_pot.pot_code = result
    new_pot.save()
    new_pot.participants.add(request.user)

    user_profile.point -= fee
    user_profile.save()

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
    if is_pot_ended(pot, today):
        return redirect('main:complete', pot_id=pot.id)

    my_today_proof = None
    if Proof.objects.filter(pot=pot, user=request.user, auth_date=today).exists():
        my_today_proof = Proof.objects.get(pot=pot, user=request.user, auth_date=today)

    can_authenticate = is_auth_day(pot, today)

    if request.method == 'POST':
        if not can_authenticate:
            context = {
                'pot': pot,
                'now': today,
                'my_today_proof': my_today_proof,
                'can_authenticate': False,
                'error': '오늘은 인증 요일이 아닙니다.',
            }
            return render(request, 'pages/before_photo.html', context)

        if my_today_proof:
            return redirect('main:after_photo', pot_id=pot.id)

        image = request.FILES.get('image')
        if image:
            proof = Proof(pot=pot, user=request.user, image=image)
            proof.save()
            return redirect('main:after_photo', pot_id=pot.id)

        context = {
            'pot': pot,
            'now': today,
            'my_today_proof': my_today_proof,
            'can_authenticate': True,
            'error': '인증사진을 선택해주세요.',
        }
        return render(request, 'pages/before_photo.html', context)

    context = {
        'pot': pot,
        'now': today,
        'my_today_proof': my_today_proof,
        'can_authenticate': can_authenticate,
    }
    if not can_authenticate:
        context['error'] = '오늘은 인증 요일이 아닙니다.'

    return render(request, 'pages/before_photo.html', context)
def after_photo(request, pot_id):
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    pot = get_object_or_404(Pot, pk=pot_id)
    if not pot.participants.filter(id=request.user.id).exists():
        return redirect('main:dashboard')

    today = datetime.date.today()
    if is_pot_ended(pot, today):
        return redirect('main:complete', pot_id=pot.id)

    my_today_proof = Proof.objects.filter(pot=pot, user=request.user, auth_date=today).first()
    if not my_today_proof:
        return redirect('main:before_photo', pot_id=pot.id)

    votes = my_today_proof.votes.all()
    total_participants = pot.participants.count() - 1
    responded_count = votes.count()
    agree_count = votes.filter(is_approved=True).count()
    disagree_count = votes.filter(is_approved=False).count()
    agree_pct = int((agree_count / responded_count) * 100) if responded_count > 0 else 0
    disagree_pct = int((disagree_count / responded_count) * 100) if responded_count > 0 else 0

    context = {
        'pot': pot,
        'now': today,
        'my_today_proof': my_today_proof,
        'total_participants': total_participants,
        'responded_count': responded_count,
        'agree_count': agree_count,
        'agree_pct': agree_pct,
        'disagree_count': disagree_count,
        'disagree_pct': disagree_pct,
    }
    return render(request, 'pages/after_photo.html', context)
def photo_vote(request, pot_id, target_user_id):
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    pot = get_object_or_404(Pot, pk=pot_id)
    if not pot.participants.filter(id=request.user.id).exists():
        return redirect('main:dashboard')

    if not pot.participants.filter(id=target_user_id).exists():
        return redirect('main:pot_detail', pot_id=pot.id)

    target_user = get_object_or_404(User, pk=target_user_id)
    if target_user == request.user:
        return redirect('main:pot_detail', pot_id=pot.id)

    today = datetime.date.today()
    if is_pot_ended(pot, today):
        return redirect('main:complete', pot_id=pot.id)

    proof = Proof.objects.filter(pot=pot, user=target_user, auth_date=today).first()
    if not proof:
        return redirect('main:pot_detail', pot_id=pot.id)

    if request.method == 'POST':
        vote_action = request.POST.get('vote')
        if vote_action not in ['approve', 'reject']:
            return redirect('main:photo_vote', pot_id=pot.id, target_user_id=target_user.id)

        if Vote.objects.filter(proof=proof, voter=request.user).exists():
            vote = Vote.objects.get(proof=proof, voter=request.user)
        else:
            vote = Vote(proof=proof, voter=request.user)

        vote.is_approved = vote_action == 'approve'
        vote.save()

        eligible_count = pot.participants.count() - 1
        reject_count = proof.votes.filter(is_approved=False).count()
        proof.is_valid = not (reject_count > eligible_count / 2)
        proof.save()

        return redirect('main:photo_vote', pot_id=pot.id, target_user_id=target_user.id)

    votes = proof.votes.all()
    responded_count = votes.count()
    agree_count = votes.filter(is_approved=True).count()
    disagree_count = votes.filter(is_approved=False).count()
    agree_pct = int((agree_count / responded_count) * 100) if responded_count > 0 else 0
    disagree_pct = int((disagree_count / responded_count) * 100) if responded_count > 0 else 0
    selected_vote = None
    if Vote.objects.filter(proof=proof, voter=request.user).exists():
        selected_vote = Vote.objects.get(proof=proof, voter=request.user)

    context = {
        'pot': pot,
        'target_user': target_user,
        'proof': proof,
        'now': today,
        'responded_count': responded_count,
        'agree_count': agree_count,
        'agree_pct': agree_pct,
        'disagree_count': disagree_count,
        'disagree_pct': disagree_pct,
        'selected_vote': selected_vote,
    }
    return render(request, 'pages/photo_vote.html', context)

def complete(request, pot_id):
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    pot = get_object_or_404(Pot, pk=pot_id)
    if not pot.participants.filter(id=request.user.id).exists():
        return redirect('main:dashboard')

    today = datetime.date.today()
    if not is_pot_ended(pot, today):
        return redirect('main:pot_detail', pot_id=pot.id)

    participants = pot.participants.all()
    required_count = get_required_auth_count(pot)
    success_count = (required_count * 80 + 99) // 100
    final_rank = []
    successful_users = []

    for participant in participants:
        valid_count = get_valid_proof_count(pot, participant)
        achievement_rate = int((valid_count / required_count) * 100) if required_count > 0 else 0
        is_success = required_count > 0 and valid_count >= success_count
        if is_success:
            successful_users.append(participant)

        final_rank.append({
            'user': participant,
            'count': valid_count,
            'required_count': required_count,
            'achievement_rate': achievement_rate,
            'is_success': is_success,
            'prize': 0,
        })

    final_rank.sort(key=lambda info: info['count'], reverse=True)
    current_rank = 0
    previous_count = None
    for index in range(len(final_rank)):
        info = final_rank[index]
        if previous_count != info['count']:
            current_rank = index + 1
            previous_count = info['count']
        info['rank'] = current_rank

    pot.total_prize = (pot.fee * pot.participants.count()) + 500
    prize_per_user = 0
    if successful_users:
        prize_per_user = pot.total_prize // len(successful_users)

    if not pot.is_completed:
        for participant in successful_users:
            profile = participant.profile
            profile.point += prize_per_user
            profile.accumulated_point += prize_per_user
            profile.save()

        pot.is_completed = True
        pot.save()

    for info in final_rank:
        if info['is_success']:
            info['prize'] = prize_per_user

    context = {
        'pot': pot,
        'final_rank': final_rank,
        'required_count': required_count,
        'success_count': success_count,
        'prize_per_user': prize_per_user,
        'successful_count': len(successful_users),
        'participant_count': pot.participants.count(),
        'participant_prize': pot.fee * pot.participants.count(),
    }
    return render(request, 'pages/complete.html', context)

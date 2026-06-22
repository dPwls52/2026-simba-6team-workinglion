from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render, redirect
from accounts.models import Profile
from main.models import Pot, Proof
import datetime

def mypage(request, id):
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    if request.user.id != id:
        return redirect('main:dashboard')

    profile_user = get_object_or_404(User, pk=id)
    profile = get_object_or_404(Profile, user=profile_user)

    my_pots = Pot.objects.filter(participants=profile_user)
    
    completed_pots_count = my_pots.filter(is_completed=True).count()
    
    today = datetime.date.today()
    active_dates = set()

    expected_auth_count = 0
    WEEKDAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']

    for pot in my_pots:
        if today < pot.start_date:
            continue
            
        for i in range(pot.days):
            current_date = pot.start_date + datetime.timedelta(days=i)
            
            if current_date > today:
                break 
                
            active_dates.add(current_date)

            weekday_str = WEEKDAYS[current_date.weekday()]
            if weekday_str in pot.auth_days: 
                expected_auth_count += 1

    total_days = len(active_dates)
    
    valid_proofs_count = Proof.objects.filter(user=profile_user, is_valid=True).count()
    if expected_auth_count > 0:
        achievement_rate = int((valid_proofs_count / expected_auth_count) * 100)
    else:
        achievement_rate = 0

    context = {
        'profile_user': profile_user,
        'profile': profile,
        'my_pots': my_pots,
        'completed_pots_count': completed_pots_count,
        'total_days': total_days,
        'achievement_rate': achievement_rate,
    }

    return render(request, 'users/mypage.html', context)

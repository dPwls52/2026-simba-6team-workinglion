from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render, redirect
from accounts.models import Profile

def mypage(request, id):
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    if request.user.id != id:
        return redirect('main:dashboard')

    profile_user = get_object_or_404(User, pk=id)
    profile = get_object_or_404(Profile, user=profile_user)

    context = {
        'profile_user': profile_user,
        'profile': profile,
    }

    return render(request, 'users/mypage.html', context)

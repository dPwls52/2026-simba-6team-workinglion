from django.shortcuts import render

def onboarding(request):
    return render(request, 'pages/onboarding.html')
def signup_login(request):
    return render(request, 'pages/signup_login.html')
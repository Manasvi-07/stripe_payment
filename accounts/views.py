from django.views import View
from django.contrib import messages
from accounts.models import User
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout

class SignupView(View):
    template_name = 'accounts/signup.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        email = request.POST.get('email')
        password = request.POST.get('password')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered. Please login instead.")
            return redirect('login')

        user = User.objects.create_user(email=email, password=password)
        messages.success(request, "Account created successfully! Please login.")
        return redirect('login')


class LoginView(View):
    template_name = 'accounts/login.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, email=email, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, "Logged in successfully!")
            return redirect('home')
        else:
            messages.error(request, "Invalid email or password.")
            return redirect('login')


class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('login')
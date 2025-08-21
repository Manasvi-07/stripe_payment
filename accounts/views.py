from django.views import View
from django.contrib import messages
from accounts.models import User
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from payments.models import Subscription
from django.utils.timezone import now

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
            return redirect('post_list')
        else:
            messages.error(request, "Invalid email or password.")
            return redirect('login')


class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('login')
    

class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        subscription = Subscription.objects.filter(user=user, active=True, end_date__gt=now()).order_by('-end_date').first()

        context['subscription'] = subscription
        return context
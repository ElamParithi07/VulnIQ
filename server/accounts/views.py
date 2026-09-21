from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import TemplateView

from .forms import EmailAuthenticationForm, SignUpForm
from .services.verification import send_verification_email, verify_email_token


class SignUpView(View):
    template_name = "accounts/signup.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(request, self.template_name, {"form": SignUpForm()})

    def post(self, request: HttpRequest) -> HttpResponse:
        form = SignUpForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form}, status=400)

        user = form.save()
        send_verification_email(user)
        login(request, user)
        messages.success(request, "Account created. Verify your email to enable digests.")
        return redirect("dashboard-home")


class EmailLoginView(LoginView):
    authentication_form = EmailAuthenticationForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True


class EmailLogoutView(LogoutView):
    next_page = reverse_lazy("accounts:login")


class VerifyEmailView(View):
    def get(self, request: HttpRequest, token: str) -> HttpResponse:
        user = verify_email_token(token)
        if user is None:
            messages.error(request, "Verification link is invalid or expired.")
        else:
            messages.success(request, "Your email has been verified.")
        return redirect("dashboard-home")


class DashboardHomeView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/dashboard.html"
    login_url = "accounts:login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["organization"] = self.request.user.organization
        return context


class DigestSettingsView(LoginRequiredMixin, View):
    template_name = "accounts/dashboard_settings.html"
    login_url = "accounts:login"

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(request, self.template_name, {"organization": request.user.organization})

    def post(self, request: HttpRequest) -> HttpResponse:
        action = request.POST.get("action")
        organization = request.user.organization

        if action == "enable_digest":
            if not request.user.can_enable_digests:
                messages.error(request, "Verify your email before enabling daily digests.")
            else:
                organization.digest_enabled = True
                organization.save(update_fields=["digest_enabled", "updated_at"])
                messages.success(request, "Daily digest emails enabled.")
        elif action == "disable_digest":
            organization.digest_enabled = False
            organization.save(update_fields=["digest_enabled", "updated_at"])
            messages.success(request, "Daily digest emails disabled.")
        elif action == "resend_verification":
            if request.user.is_email_verified:
                messages.info(request, "Your email is already verified.")
            else:
                send_verification_email(request.user)
                messages.success(request, "Verification email sent.")

        return redirect("dashboard-settings")

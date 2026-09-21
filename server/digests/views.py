from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from digests.services.email_context import build_email_context
from digests.services.query import get_latest_digest


class LatestDigestView(LoginRequiredMixin, TemplateView):
    template_name = "digests/latest_digest.html"
    login_url = "accounts:login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = self.request.user.organization
        digest = get_latest_digest(organization) if organization is not None else None
        context["digest"] = digest
        context["digest_context"] = build_email_context(digest) if digest is not None else None
        return context

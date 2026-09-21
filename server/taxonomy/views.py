from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views import View

from taxonomy.models import TechTag, UserTechTag


class TagSelectionView(LoginRequiredMixin, View):
    template_name = "taxonomy/tag_selection.html"
    login_url = "accounts:login"

    def get(self, request: HttpRequest) -> HttpResponse:
        tags = TechTag.objects.filter(is_active=True)
        selected_ids = set(request.user.selected_tech_tags.values_list("tag_id", flat=True))
        return render(request, self.template_name, {"tags": tags, "selected_ids": selected_ids})

    def post(self, request: HttpRequest) -> HttpResponse:
        tags = TechTag.objects.filter(is_active=True)
        posted_ids = {int(v) for v in request.POST.getlist("tags") if v.isdigit()}
        valid_ids = set(tags.values_list("id", flat=True)) & posted_ids

        existing_ids = set(request.user.selected_tech_tags.values_list("tag_id", flat=True))
        to_add = valid_ids - existing_ids
        to_remove = existing_ids - valid_ids

        if to_remove:
            UserTechTag.objects.filter(user=request.user, tag_id__in=to_remove).delete()
        for tag_id in to_add:
            UserTechTag.objects.create(user=request.user, tag_id=tag_id)

        messages.success(request, "Product selections updated.")
        return redirect("taxonomy:tag-selection")

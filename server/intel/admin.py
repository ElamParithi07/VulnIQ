from django import forms
from django.contrib import admin
from django.shortcuts import render

from intel.models import Vulnerability, VulnerabilityAIEnrichment, VulnerabilityProduct, VulnerabilityProductStatus
from intel.services.matching import match_vulnerability_product
from taxonomy.models import TechTag
from taxonomy.services.tags import alias_already_covers, create_alias_for_tag, get_or_create_canonical_tag


class VulnerabilityProductInline(admin.TabularInline):
    model = VulnerabilityProduct
    extra = 0
    fields = (
        "raw_vendor",
        "raw_product",
        "normalized_vendor",
        "normalized_product",
        "tech_tag",
        "match_status",
        "source_cpe",
    )
    readonly_fields = ("created_at", "updated_at")
    show_change_link = True


class VulnerabilityAIEnrichmentInline(admin.StackedInline):
    model = VulnerabilityAIEnrichment
    extra = 0
    fields = (
        "provider",
        "model_name",
        "prompt_version",
        "input_hash",
        "status",
        "summary_text",
        "remediation_text",
        "error_message",
        "generated_at",
        "created_at",
        "updated_at",
    )
    readonly_fields = ("created_at", "updated_at")
    show_change_link = True


@admin.register(Vulnerability)
class VulnerabilityAdmin(admin.ModelAdmin):
    list_display = (
        "cve_id",
        "status",
        "cvss_score",
        "epss_score",
        "is_cisa_kev",
        "priority_score",
        "published_at",
        "last_modified_at",
    )
    list_filter = ("status", "is_cisa_kev")
    search_fields = ("cve_id", "title", "description")
    readonly_fields = ("created_at", "updated_at")
    inlines = (VulnerabilityProductInline, VulnerabilityAIEnrichmentInline)
    actions = ["regenerate_ai_enrichment"]
    fieldsets = (
        (
            "Core",
            {
                "fields": (
                    "cve_id",
                    "title",
                    "description",
                    "status",
                    "published_at",
                    "last_modified_at",
                    "last_seen_in_feed_at",
                )
            },
        ),
        (
            "Scoring",
            {"fields": ("cvss_score", "epss_score", "is_cisa_kev", "priority_score")},
        ),
        (
            "Raw Payloads",
            {"fields": ("nvd_raw_json", "kev_raw_json", "epss_raw_json")},
        ),
        ("Audit", {"fields": ("created_at", "updated_at")}),
    )

    @admin.action(description="Regenerate AI enrichment for selected vulnerabilities")
    def regenerate_ai_enrichment(self, request, queryset):
        from intel.services.enrichment import generate_enrichment

        # force regeneration by clearing the stored input hash so the reuse
        # guard doesn't short-circuit; does not touch any digest snapshot,
        # only the current (latest) enrichment record for each vulnerability
        VulnerabilityAIEnrichment.objects.filter(vulnerability__in=queryset).update(input_hash="")

        count = 0
        for vulnerability in queryset:
            generate_enrichment(vulnerability)
            count += 1

        self.message_user(request, f"Regenerated AI enrichment for {count} vulnerability(ies).")


class UnmatchedProductResolutionForm(forms.Form):
    RESOLUTION_CHOICES = [
        ("existing", "Link to an existing tag (creates an alias)"),
        ("new", "Create a new canonical tag"),
    ]
    resolution = forms.ChoiceField(choices=RESOLUTION_CHOICES, widget=forms.RadioSelect)
    existing_tag = forms.ModelChoiceField(
        queryset=TechTag.objects.filter(is_active=True), required=False
    )
    new_tag_name = forms.CharField(required=False, max_length=120)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("resolution") == "existing" and not cleaned.get("existing_tag"):
            self.add_error("existing_tag", "Select an existing tag.")
        if cleaned.get("resolution") == "new" and not cleaned.get("new_tag_name"):
            self.add_error("new_tag_name", "Provide a name for the new tag.")
        return cleaned


@admin.register(VulnerabilityProduct)
class VulnerabilityProductAdmin(admin.ModelAdmin):
    list_display = (
        "vulnerability",
        "normalized_vendor",
        "normalized_product",
        "tech_tag",
        "match_status",
    )
    list_filter = ("match_status",)
    search_fields = (
        "vulnerability__cve_id",
        "raw_vendor",
        "raw_product",
        "normalized_vendor",
        "normalized_product",
        "source_cpe",
    )
    autocomplete_fields = ("tech_tag",)
    readonly_fields = ("created_at", "updated_at")
    actions = ["mark_as_ignored", "resolve_unmatched_products"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("vulnerability", "tech_tag")

    @admin.action(description="Mark selected products as ignored")
    def mark_as_ignored(self, request, queryset):
        updated = queryset.update(match_status=VulnerabilityProductStatus.IGNORED, tech_tag=None)
        self.message_user(request, f"Marked {updated} product(s) as ignored.")

    @admin.action(description="Resolve selected unmatched products (alias or new tag)")
    def resolve_unmatched_products(self, request, queryset):
        if "apply" in request.POST:
            form = UnmatchedProductResolutionForm(request.POST)
            if form.is_valid():
                if form.cleaned_data["resolution"] == "existing":
                    tag = form.cleaned_data["existing_tag"]
                else:
                    tag = get_or_create_canonical_tag(form.cleaned_data["new_tag_name"])

                distinct_normalized_products = {p.normalized_product for p in queryset}
                for normalized_product in distinct_normalized_products:
                    if not alias_already_covers(tag, normalized_product):
                        create_alias_for_tag(tag, normalized_product)

                for product in queryset:
                    match_vulnerability_product(product)

                self.message_user(request, f"Resolved {queryset.count()} product(s) to '{tag.name}'.")
                return None
        else:
            form = UnmatchedProductResolutionForm()

        return render(
            request,
            "admin/intel/vulnerabilityproduct/resolve_unmatched.html",
            {
                "products": queryset,
                "form": form,
                "action_checkbox_name": admin.helpers.ACTION_CHECKBOX_NAME,
                "opts": self.model._meta,
            },
        )


@admin.register(VulnerabilityAIEnrichment)
class VulnerabilityAIEnrichmentAdmin(admin.ModelAdmin):
    list_display = (
        "vulnerability",
        "provider",
        "model_name",
        "status",
        "generated_at",
    )
    list_filter = ("status", "provider", "model_name")
    search_fields = (
        "vulnerability__cve_id",
        "summary_text",
        "remediation_text",
        "error_message",
    )
    readonly_fields = ("created_at", "updated_at")

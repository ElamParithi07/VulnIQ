from django.contrib import admin

from .models import EmailVerificationToken, Organization, User


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "digest_enabled", "created_at")
    search_fields = ("name", "slug")
    actions = ["disable_digest_sending"]

    @admin.action(description="Disable digest sending")
    def disable_digest_sending(self, request, queryset):
        updated = queryset.update(digest_enabled=False)
        self.message_user(request, f"Disabled digest sending for {updated} organization(s).")


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "organization", "is_email_verified", "is_staff", "last_login")
    search_fields = ("email",)
    list_filter = ("is_email_verified", "is_staff", "is_superuser")
    actions = ["reissue_verification_email"]

    @admin.action(description="Reissue verification email")
    def reissue_verification_email(self, request, queryset):
        from accounts.services.verification import send_verification_email

        count = 0
        for user in queryset.filter(is_email_verified=False):
            send_verification_email(user)
            count += 1

        self.message_user(request, f"Reissued verification email for {count} user(s).")


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "expires_at", "consumed_at", "created_at")
    search_fields = ("user__email", "token")

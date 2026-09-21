from django.contrib import admin

from .models import DailyDigest, DailyDigestItem, EmailSendAttempt


class DailyDigestItemInline(admin.TabularInline):
    model = DailyDigestItem
    extra = 0


@admin.register(DailyDigest)
class DailyDigestAdmin(admin.ModelAdmin):
    list_display = ("organization", "digest_date", "status", "matching_vulnerability_count", "backfill_vulnerability_count", "sent_at")
    list_filter = ("status", "digest_date")
    search_fields = ("organization__name", "user__email", "rendered_subject")
    inlines = [DailyDigestItemInline]
    actions = ["resend_digest_email"]

    @admin.action(description="Resend digest email")
    def resend_digest_email(self, request, queryset):
        from digests.services.delivery import send_digest

        sent, failed = 0, 0
        for digest in queryset:
            attempt = send_digest(digest)
            if attempt.status == EmailSendAttempt.Status.SENT:
                sent += 1
            else:
                failed += 1

        self.message_user(request, f"Resent {sent} digest(s); {failed} failed.")


@admin.register(EmailSendAttempt)
class EmailSendAttemptAdmin(admin.ModelAdmin):
    list_display = ("daily_digest", "attempt_number", "provider", "status", "attempted_at")
    list_filter = ("provider", "status")
    search_fields = ("provider_message_id", "daily_digest__user__email", "error_message")

# Register your models here.

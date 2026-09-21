from django.contrib import admin

from taxonomy.models import TechTag, TechTagAlias, UserTechTag


class TechTagAliasInline(admin.TabularInline):
    model = TechTagAlias
    extra = 0
    fields = ("alias", "normalized_alias", "created_at")
    readonly_fields = ("normalized_alias", "created_at")


@admin.register(TechTag)
class TechTagAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "is_active", "updated_at")
    list_filter = ("category", "is_active")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [TechTagAliasInline]


@admin.register(TechTagAlias)
class TechTagAliasAdmin(admin.ModelAdmin):
    list_display = ("alias", "tag", "normalized_alias", "updated_at")
    list_filter = ("tag__category",)
    search_fields = ("alias", "normalized_alias", "tag__name")
    autocomplete_fields = ("tag",)
    readonly_fields = ("normalized_alias",)


@admin.register(UserTechTag)
class UserTechTagAdmin(admin.ModelAdmin):
    list_display = ("user", "tag", "created_at")
    list_select_related = ("user", "tag")
    search_fields = ("user__email", "tag__name")
    autocomplete_fields = ("user", "tag")

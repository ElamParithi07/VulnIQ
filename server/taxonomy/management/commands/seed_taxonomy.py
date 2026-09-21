from django.core.management.base import BaseCommand

from taxonomy.models import TechTag, TechTagAlias, TechTagCategory, normalize_alias
from django.utils.text import slugify


DEFAULT_TAGS = (
    {
        "name": "Microsoft 365",
        "aliases": ("Office 365", "M365"),
    },
    {
        "name": "Windows Server",
        "aliases": ("Microsoft Windows Server",),
    },
    {
        "name": "VMware vCenter",
        "aliases": ("VMware vCenter Server", "vCenter"),
    },
)


class Command(BaseCommand):
    help = "Seed the controlled MVP product tag taxonomy."

    def handle(self, *args, **options):
        created_tags = 0
        created_aliases = 0

        for item in DEFAULT_TAGS:
            tag, tag_created = TechTag.objects.get_or_create(
                slug=slugify(item["name"]),
                defaults={
                    "name": item["name"],
                    "category": TechTagCategory.PRODUCT,
                },
            )
            if not tag_created:
                dirty = False
                if tag.name != item["name"]:
                    tag.name = item["name"]
                    dirty = True
                if tag.category != TechTagCategory.PRODUCT:
                    tag.category = TechTagCategory.PRODUCT
                    dirty = True
                if dirty:
                    tag.save(update_fields=["name", "category", "updated_at"])
            else:
                created_tags += 1

            for alias in item["aliases"]:
                _, alias_created = TechTagAlias.objects.get_or_create(
                    normalized_alias=normalize_alias(alias),
                    defaults={
                        "tag": tag,
                        "alias": alias,
                    },
                )
                if alias_created:
                    created_aliases += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded taxonomy: {created_tags} tags created, {created_aliases} aliases created."
            )
        )

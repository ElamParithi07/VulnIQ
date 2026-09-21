from django.conf import settings
from django.core.validators import MinLengthValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils.text import slugify

from common.models import TimeStampedModel


def normalize_alias(value: str) -> str:
    return " ".join(value.lower().split())


class TechTagCategory(models.TextChoices):
    PRODUCT = "product", "Product"


class TechTag(TimeStampedModel):
    name = models.CharField(max_length=120, unique=True, validators=[MinLengthValidator(2)])
    slug = models.SlugField(max_length=140, unique=True)
    category = models.CharField(max_length=50, choices=TechTagCategory.choices)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(Lower("name"), name="taxonomy_techtag_name_ci_unique"),
        ]

    def save(self, *args, **kwargs):
        self.name = self.name.strip()
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class TechTagAlias(TimeStampedModel):
    tag = models.ForeignKey(TechTag, on_delete=models.CASCADE, related_name="aliases")
    alias = models.CharField(max_length=160)
    normalized_alias = models.CharField(max_length=160, editable=False)

    class Meta:
        ordering = ["alias"]
        constraints = [
            models.UniqueConstraint(
                Lower("alias"),
                name="taxonomy_techtagalias_alias_ci_unique",
            ),
            models.UniqueConstraint(
                fields=["normalized_alias"],
                name="taxonomy_techtagalias_normalized_alias_unique",
            ),
        ]

    def save(self, *args, **kwargs):
        self.alias = self.alias.strip()
        self.normalized_alias = normalize_alias(self.alias)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.alias


class UserTechTag(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="selected_tech_tags",
    )
    tag = models.ForeignKey(TechTag, on_delete=models.CASCADE, related_name="user_assignments")

    class Meta:
        ordering = ["user__email", "tag__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "tag"],
                name="taxonomy_usertechtag_user_tag_unique",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user.email} -> {self.tag.name}"

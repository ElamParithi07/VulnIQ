from __future__ import annotations

from taxonomy.models import TechTag, TechTagAlias, TechTagCategory, normalize_alias


def create_alias_for_tag(tag: TechTag, alias_text: str) -> TechTagAlias:
    """Create an alias linking `alias_text` to `tag`.

    Used by admin's unmatched-product review workflow to teach the
    normalization pipeline a new vendor/product spelling without waiting
    for a code change.
    """
    return TechTagAlias.objects.create(tag=tag, alias=alias_text)


def get_or_create_canonical_tag(name: str) -> TechTag:
    tag, _created = TechTag.objects.get_or_create(
        name=name,
        defaults={"category": TechTagCategory.PRODUCT},
    )
    return tag


def alias_already_covers(tag: TechTag, normalized_value: str) -> bool:
    """True if `normalized_value` already resolves to `tag` via an existing
    alias or the tag's own canonical name, so a duplicate alias is avoided."""
    if normalize_alias(tag.name) == normalized_value:
        return True
    return tag.aliases.filter(normalized_alias=normalized_value).exists()

from __future__ import annotations

from taxonomy.models import TechTag, TechTagAlias, normalize_alias

from intel.models import VulnerabilityProduct, VulnerabilityProductStatus


def resolve_tech_tag(normalized_product: str) -> tuple[str, TechTag | None]:
    """Resolve a normalized product string to a canonical TechTag.

    Matching precedence (no fuzzy matching):
    1. exact match on TechTagAlias.normalized_alias
    2. exact match on a canonical TechTag name (case/whitespace normalized)
    3. unmatched

    If more than one active tag's normalized name collides, the match is
    reported as ambiguous rather than guessed.
    """
    alias = (
        TechTagAlias.objects.select_related("tag")
        .filter(normalized_alias=normalized_product, tag__is_active=True)
        .first()
    )
    if alias is not None:
        return VulnerabilityProductStatus.MATCHED, alias.tag

    candidates = [
        tag
        for tag in TechTag.objects.filter(is_active=True)
        if normalize_alias(tag.name) == normalized_product
    ]

    if len(candidates) == 1:
        return VulnerabilityProductStatus.MATCHED, candidates[0]
    if len(candidates) > 1:
        return VulnerabilityProductStatus.AMBIGUOUS, None
    return VulnerabilityProductStatus.UNMATCHED, None


def match_vulnerability_product(product: VulnerabilityProduct) -> VulnerabilityProduct:
    """Resolve and persist the match status/tech_tag for one product row.

    Products already marked IGNORED are left untouched by matching.
    """
    if product.match_status == VulnerabilityProductStatus.IGNORED:
        return product

    status, tag = resolve_tech_tag(product.normalized_product)
    product.match_status = status
    product.tech_tag = tag
    product.save(update_fields=["match_status", "tech_tag", "updated_at"])
    return product

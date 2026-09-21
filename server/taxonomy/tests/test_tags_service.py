import pytest

from taxonomy.models import TechTag, TechTagCategory
from taxonomy.services.tags import alias_already_covers, create_alias_for_tag, get_or_create_canonical_tag


@pytest.mark.django_db
def test_create_alias_for_tag_persists_normalized_alias():
    tag = TechTag.objects.create(name="Windows Server", category=TechTagCategory.PRODUCT)

    alias = create_alias_for_tag(tag, "win srv")

    assert alias.tag == tag
    assert alias.normalized_alias == "win srv"


@pytest.mark.django_db
def test_get_or_create_canonical_tag_is_idempotent():
    first = get_or_create_canonical_tag("New Product")
    second = get_or_create_canonical_tag("New Product")

    assert first.id == second.id
    assert TechTag.objects.filter(name="New Product").count() == 1


@pytest.mark.django_db
def test_alias_already_covers_true_for_canonical_name_match():
    tag = TechTag.objects.create(name="Windows Server", category=TechTagCategory.PRODUCT)

    assert alias_already_covers(tag, "windows server") is True


@pytest.mark.django_db
def test_alias_already_covers_true_for_existing_alias():
    tag = TechTag.objects.create(name="Windows Server", category=TechTagCategory.PRODUCT)
    create_alias_for_tag(tag, "win srv")

    assert alias_already_covers(tag, "win srv") is True


@pytest.mark.django_db
def test_alias_already_covers_false_when_neither_matches():
    tag = TechTag.objects.create(name="Windows Server", category=TechTagCategory.PRODUCT)

    assert alias_already_covers(tag, "something else") is False

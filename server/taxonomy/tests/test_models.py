import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError

from accounts.models import Organization, User
from taxonomy.models import TechTag, TechTagAlias, TechTagCategory, UserTechTag


@pytest.mark.django_db
def test_techtag_category_is_required():
    tag = TechTag(name="Microsoft 365", slug="microsoft-365", category="")

    with pytest.raises(ValidationError):
        tag.full_clean()


@pytest.mark.django_db
def test_aliases_are_unique_case_insensitively():
    tag = TechTag.objects.create(name="Windows Server", slug="windows-server", category=TechTagCategory.PRODUCT)
    TechTagAlias.objects.create(tag=tag, alias="Office 365")

    with pytest.raises(IntegrityError):
        TechTagAlias.objects.create(tag=tag, alias="office 365")


@pytest.mark.django_db
def test_user_tag_assignment_links_existing_user_and_tag():
    org = Organization.objects.create(name="Acme", slug="acme")
    user = User.objects.create_user(email="owner@acme.test", password="secret123", organization=org)
    tag = TechTag.objects.create(name="VMware vCenter", slug="vmware-vcenter", category=TechTagCategory.PRODUCT)

    assignment = UserTechTag.objects.create(user=user, tag=tag)

    assert assignment.user == user
    assert assignment.tag == tag
    assert list(user.selected_tech_tags.values_list("tag__name", flat=True)) == ["VMware vCenter"]


@pytest.mark.django_db
def test_seed_taxonomy_is_idempotent():
    call_command("seed_taxonomy")
    first_tag_count = TechTag.objects.count()
    first_alias_count = TechTagAlias.objects.count()

    call_command("seed_taxonomy")

    assert TechTag.objects.count() == first_tag_count
    assert TechTagAlias.objects.count() == first_alias_count

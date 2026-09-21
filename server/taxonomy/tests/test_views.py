import pytest
from django.urls import reverse

from accounts.models import Organization, User
from taxonomy.models import TechTag, TechTagCategory, UserTechTag


def _make_user():
    org = Organization.objects.create(name="Acme", slug="acme")
    user = User.objects.create_user(email="owner@acme.test", password="secret123", organization=org)
    return user


@pytest.mark.django_db
def test_tag_selection_requires_login(client):
    response = client.get(reverse("taxonomy:tag-selection"))

    assert response.status_code == 302


@pytest.mark.django_db
def test_tag_selection_get_shows_tags_and_current_selection(client):
    user = _make_user()
    tag_a = TechTag.objects.create(name="Windows Server", category=TechTagCategory.PRODUCT)
    tag_b = TechTag.objects.create(name="VMware vCenter", category=TechTagCategory.PRODUCT)
    UserTechTag.objects.create(user=user, tag=tag_a)
    client.force_login(user)

    response = client.get(reverse("taxonomy:tag-selection"))

    assert response.status_code == 200
    assert b"Windows Server" in response.content
    assert b"VMware vCenter" in response.content


@pytest.mark.django_db
def test_tag_selection_post_adds_and_removes_tags(client):
    user = _make_user()
    tag_a = TechTag.objects.create(name="Windows Server", category=TechTagCategory.PRODUCT)
    tag_b = TechTag.objects.create(name="VMware vCenter", category=TechTagCategory.PRODUCT)
    UserTechTag.objects.create(user=user, tag=tag_a)
    client.force_login(user)

    client.post(reverse("taxonomy:tag-selection"), {"tags": [str(tag_b.id)]})

    selected = set(user.selected_tech_tags.values_list("tag_id", flat=True))
    assert selected == {tag_b.id}


@pytest.mark.django_db
def test_tag_selection_post_ignores_inactive_or_unknown_tag_ids(client):
    user = _make_user()
    inactive_tag = TechTag.objects.create(
        name="Deprecated Tool", category=TechTagCategory.PRODUCT, is_active=False
    )
    client.force_login(user)

    client.post(reverse("taxonomy:tag-selection"), {"tags": [str(inactive_tag.id), "999999", "not-a-number"]})

    assert user.selected_tech_tags.count() == 0

"""Shared factory-boy factories for end-to-end and cross-app tests.

Individual app test suites are intentionally left as-is (they already pass
and retrofitting ~200 existing tests onto factories is a large, low-value
diff on its own). These factories exist for new cross-module tests that
need a full org/user/tag/vulnerability graph without re-deriving it inline.
"""
from __future__ import annotations

from decimal import Decimal

import factory
from factory.django import DjangoModelFactory

from accounts.models import Organization, User
from intel.models import Vulnerability, VulnerabilityProduct, VulnerabilityProductStatus, VulnerabilityStatus
from taxonomy.models import TechTag, TechTagCategory


class OrganizationFactory(DjangoModelFactory):
    class Meta:
        model = Organization

    name = factory.Sequence(lambda n: f"Org {n}")
    slug = factory.Sequence(lambda n: f"org-{n}")
    digest_enabled = False


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"user{n}@example.test")
    organization = factory.SubFactory(OrganizationFactory)
    is_email_verified = False

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        self.set_password(extracted or "TestPass123!")
        if create:
            self.save(update_fields=["password"])


class TechTagFactory(DjangoModelFactory):
    class Meta:
        model = TechTag
        django_get_or_create = ("name",)

    name = factory.Sequence(lambda n: f"Test Tag {n}")
    category = TechTagCategory.PRODUCT


class VulnerabilityFactory(DjangoModelFactory):
    class Meta:
        model = Vulnerability
        django_get_or_create = ("cve_id",)

    cve_id = factory.Sequence(lambda n: f"CVE-2026-{n:05d}")
    title = factory.Faker("sentence", nb_words=6)
    description = factory.Faker("paragraph")
    status = VulnerabilityStatus.PUBLISHED
    cvss_score = Decimal("9.0")
    epss_score = Decimal("0.5")
    is_cisa_kev = False


class VulnerabilityProductFactory(DjangoModelFactory):
    class Meta:
        model = VulnerabilityProduct

    vulnerability = factory.SubFactory(VulnerabilityFactory)
    raw_vendor = "microsoft"
    raw_product = "windows server"
    normalized_vendor = "microsoft"
    normalized_product = "windows server"
    match_status = VulnerabilityProductStatus.MATCHED
    tech_tag = factory.SubFactory(TechTagFactory)

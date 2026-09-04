from social_api.admin.attribute.certification import CertificationAdmin
from social_api.admin.attribute.inlines import (
    PersonalityCertificationInline,
    PersonalityInterestInline,
    PersonalityLanguageInline,
    PersonalitySkillInline,
)
from social_api.admin.attribute.interest import InterestAdmin
from social_api.admin.attribute.language import LanguageAdmin
from social_api.admin.attribute.personality_certification import PersonalityCertificationAdmin
from social_api.admin.attribute.skill import SkillAdmin

__all__ = [
    "CertificationAdmin",
    "InterestAdmin",
    "LanguageAdmin",
    "PersonalityCertificationAdmin",
    "PersonalityCertificationInline",
    "PersonalityInterestInline",
    "PersonalityLanguageInline",
    "PersonalitySkillInline",
    "SkillAdmin",
]

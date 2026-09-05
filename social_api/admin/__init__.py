from social_api.admin.app.import_batch import ImportBatchAdmin
from social_api.admin.app.import_chunk import ImportChunkAdmin, ImportChunkInline
from social_api.admin.app.import_row_error import ImportRowErrorAdmin
from social_api.admin.app.user import UserAdmin
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
from social_api.admin.company.company import CompanyAdmin
from social_api.admin.employment.employment import EmploymentAdmin
from social_api.admin.employment.employment_level import EmploymentLevelInline
from social_api.admin.geography.location import LocationAdmin
from social_api.admin.geography.personality_location import PersonalityLocationAdmin
from social_api.admin.occupation.industry import IndustryAdmin
from social_api.admin.occupation.occupation import OccupationAdmin
from social_api.admin.occupation.occupation_level import OccupationLevelAdmin
from social_api.admin.occupation.occupation_role import OccupationRoleAdmin
from social_api.admin.occupation.occupation_sub_role import OccupationSubRoleAdmin
from social_api.admin.person.personality import PersonalityAdmin
from social_api.admin.social.company_social_profiles import CompanySocialProfilesAdmin
from social_api.admin.social.social_platform import SocialPlatformAdmin
from social_api.admin.social.social_profiles import SocialProfilesAdmin

__all__ = [
    "CertificationAdmin",
    "CompanyAdmin",
    "CompanySocialProfilesAdmin",
    "EmploymentAdmin",
    "EmploymentLevelInline",
    "ImportBatchAdmin",
    "ImportChunkAdmin",
    "ImportChunkInline",
    "ImportRowErrorAdmin",
    "IndustryAdmin",
    "InterestAdmin",
    "LanguageAdmin",
    "LocationAdmin",
    "OccupationAdmin",
    "OccupationLevelAdmin",
    "OccupationRoleAdmin",
    "OccupationSubRoleAdmin",
    "PersonalityAdmin",
    "PersonalityCertificationAdmin",
    "PersonalityCertificationInline",
    "PersonalityInterestInline",
    "PersonalityLanguageInline",
    "PersonalityLocationAdmin",
    "PersonalitySkillInline",
    "SkillAdmin",
    "SocialPlatformAdmin",
    "SocialProfilesAdmin",
    "UserAdmin",
]

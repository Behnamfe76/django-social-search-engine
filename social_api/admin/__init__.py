from social_api.admin.company.company import CompanyAdmin
from social_api.admin.employment.employment import EmploymentAdmin
from social_api.admin.employment.employment_level import EmploymentLevelInline
from social_api.admin.geography.location import LocationAdmin
from social_api.admin.geography.personality_location import PersonalityLocationAdmin
from social_api.admin.person.personality import PersonalityAdmin
from social_api.admin.social.company_social_profiles import CompanySocialProfilesAdmin
from social_api.admin.social.social_platform import SocialPlatformAdmin
from social_api.admin.social.social_profiles import SocialProfilesAdmin

__all__ = [
    "CompanyAdmin",
    "CompanySocialProfilesAdmin",
    "EmploymentAdmin",
    "EmploymentLevelInline",
    "LocationAdmin",
    "PersonalityAdmin",
    "PersonalityLocationAdmin",
    "SocialPlatformAdmin",
    "SocialProfilesAdmin",
]

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
    "CompanyAdmin",
    "CompanySocialProfilesAdmin",
    "EmploymentAdmin",
    "EmploymentLevelInline",
    "IndustryAdmin",
    "LocationAdmin",
    "OccupationAdmin",
    "OccupationLevelAdmin",
    "OccupationRoleAdmin",
    "OccupationSubRoleAdmin",
    "PersonalityAdmin",
    "PersonalityLocationAdmin",
    "SocialPlatformAdmin",
    "SocialProfilesAdmin",
]

"""Write-side business logic: functions that create, mutate or delete state.

Read-side query building lives in ``social_api.selectors``.
"""

from social_api.services.slug import build_slug, build_unique_slug

__all__ = ["build_slug", "build_unique_slug"]

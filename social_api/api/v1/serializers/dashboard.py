"""Response shapes for the dashboard snapshot.

These are declaration-only: the selector already returns plain dicts, so nothing
here validates or transforms. They exist so drf-spectacular can describe the
payload in the schema instead of emitting an opaque object.
"""

from rest_framework import serializers


class CountSerializer(serializers.Serializer):
    """The shape every categorical panel uses: one label, one count."""

    name = serializers.CharField()
    count = serializers.IntegerField()


class SeniorityByRoleSerializer(serializers.Serializer):
    role = serializers.CharField()
    level = serializers.CharField()
    count = serializers.IntegerField()


class TenureSerializer(serializers.Serializer):
    sample_size = serializers.IntegerField()
    mean_years = serializers.FloatField(allow_null=True)
    median_years = serializers.FloatField(allow_null=True)
    buckets = CountSerializer(many=True)


class EmploymentsPerPersonSerializer(serializers.Serializer):
    employments = serializers.IntegerField()
    people = serializers.IntegerField()


class HiresByYearSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    count = serializers.IntegerField()


class SocialPlatformSerializer(serializers.Serializer):
    name = serializers.CharField()
    profiles = serializers.IntegerField()
    people = serializers.IntegerField()


class PlatformReachSerializer(serializers.Serializer):
    platforms = serializers.IntegerField()
    people = serializers.IntegerField()


class CoverageSerializer(serializers.Serializer):
    name = serializers.CharField()
    filled = serializers.IntegerField()
    total = serializers.IntegerField()
    percent = serializers.FloatField()


class ImportsSerializer(serializers.Serializer):
    batches = CountSerializer(many=True)
    processed_rows = serializers.IntegerField()
    created_rows = serializers.IntegerField()
    updated_rows = serializers.IntegerField()
    failed_rows = serializers.IntegerField()


class DashboardSerializer(serializers.Serializer):
    """One unfiltered snapshot; every panel the dashboard draws, in one payload."""

    totals = serializers.DictField(child=serializers.IntegerField())
    gender = CountSerializer(many=True)
    top_skills = CountSerializer(many=True)
    top_interests = CountSerializer(many=True)
    top_languages = CountSerializer(many=True)
    top_certifications = CountSerializer(many=True)
    top_companies = CountSerializer(many=True)
    company_sizes = CountSerializer(many=True)
    occupation_roles = CountSerializer(many=True)
    seniority_levels = CountSerializer(many=True)
    seniority_by_role = SeniorityByRoleSerializer(many=True)
    tenure = TenureSerializer()
    employment_status = CountSerializer(many=True)
    employments_per_person = EmploymentsPerPersonSerializer(many=True)
    hires_by_year = HiresByYearSerializer(many=True)
    social_platforms = SocialPlatformSerializer(many=True)
    platform_reach = PlatformReachSerializer(many=True)
    coverage = CoverageSerializer(many=True)
    imports = ImportsSerializer()

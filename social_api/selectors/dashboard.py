"""Aggregations behind the single dashboard endpoint.

The dashboard is one unfiltered, unsorted snapshot of the whole dataset, so every
function here is a plain full-table aggregate with no user input to thread through.
That is deliberate: nothing below takes a filter argument, which is what keeps the
endpoint a fixed number of queries no matter how the data grows.

Dimensions the source export corrupted past the point of being chartable are left
out rather than shown with a caveat -- ``inferred_salary``, ``birth_date`` /
``birth_year``, ``industry`` and everything geographic. See ``COVERAGE_FIELDS`` for
the honest fill-rate readout that replaces them.
"""

from datetime import timedelta

from django.db.models import (
    Avg,
    Count,
    DurationField,
    ExpressionWrapper,
    F,
    Q,
    QuerySet,
    Sum,
)
from django.db.models.aggregates import Aggregate
from django.db.models.functions import ExtractYear

from social_api.models import (
    Certification,
    Company,
    Employment,
    EmploymentLevel,
    ImportBatch,
    Interest,
    Language,
    Occupation,
    OccupationLevel,
    OccupationRole,
    Personality,
    PersonalityCertification,
    PersonalityInterest,
    PersonalityLanguage,
    PersonalitySkill,
    Skill,
    SocialPlatform,
    SocialProfiles,
)

TOP_N = 10

# Employer headcounts come from a ``job_company_size`` column the shifted rows also
# wrote free text into ("united states", "military"). The buckets are a closed set,
# so listing them filters the junk out and fixes the axis order in one go.
COMPANY_SIZE_BUCKETS = [
    "1-10",
    "11-50",
    "51-200",
    "201-500",
    "501-1000",
    "1001-5000",
    "5001-10000",
    "10001+",
]

TENURE_BUCKETS = [
    ("under 1 year", None, 1),
    ("1-2 years", 1, 2),
    ("2-5 years", 2, 5),
    ("5-10 years", 5, 10),
    ("10+ years", 10, None),
]

# Fields worth reporting a fill rate for, including the ones too sparse or too
# corrupted to chart -- a visible 2% is more useful than a silently missing panel.
COVERAGE_FIELDS = [
    "external_id",
    "industry",
    "summary",
    "inferred_salary",
    "inferred_years_experience",
    "birth_date",
    "birth_year",
    "location_last_updated",
]


class Median(Aggregate):
    """``percentile_cont(0.5)``, which Postgres exposes only as an ordered-set."""

    function = "PERCENTILE_CONT"
    name = "median"
    template = "%(function)s(0.5) WITHIN GROUP (ORDER BY %(expressions)s)"


def _personalities() -> QuerySet[Personality]:
    """Soft-deleted profiles are excluded everywhere, as they are in the API."""
    return Personality.objects.filter(deleted_at__isnull=True)


def _employments() -> QuerySet[Employment]:
    return Employment.objects.filter(personality__deleted_at__isnull=True)


def _top(queryset, label_field, count_field):
    """Top ``TOP_N`` rows of ``queryset`` by distinct profiles behind them.

    ``count_field`` must reach a concrete column rather than a related model:
    the attribute join tables use composite primary keys, which Postgres cannot
    ``COUNT(DISTINCT)``. Counting the profile also makes the number mean
    "people", not "link rows", which is what a top-ten panel should show.
    """
    rows = (
        queryset.annotate(
            count=Count(
                count_field,
                distinct=True,
                # ``count_field`` always terminates at the profile, so one rule
                # keeps soft-deleted people out of every top-ten panel.
                filter=Q(**{f"{count_field}__deleted_at__isnull": True}),
            )
        )
        .filter(count__gt=0)
        .order_by("-count", label_field)
        .values_list(label_field, "count")[:TOP_N]
    )
    return [{"name": name, "count": count} for name, count in rows]


def totals():
    return {
        "personalities": _personalities().count(),
        "employments": _employments().count(),
        "companies": Company.objects.count(),
        "skills": Skill.objects.count(),
        "interests": Interest.objects.count(),
        "languages": Language.objects.count(),
        "certifications": Certification.objects.count(),
        "occupations": Occupation.objects.count(),
        "occupation_roles": OccupationRole.objects.count(),
        "social_profiles": SocialProfiles.objects.count(),
        "import_batches": ImportBatch.objects.count(),
    }


def gender_split():
    rows = (
        _personalities()
        .values("gender")
        .annotate(count=Count("id"))
        .order_by("-count", "gender")
    )
    return [{"name": row["gender"], "count": row["count"]} for row in rows]


def top_skills():
    return _top(Skill.objects.all(), "name", "personality_links__personality")


def top_interests():
    return _top(Interest.objects.all(), "name", "personality_links__personality")


def top_languages():
    return _top(Language.objects.all(), "name", "personality_links__personality")


def top_certifications():
    return _top(Certification.objects.all(), "name", "personality_links__personality")


def top_companies():
    return _top(Company.objects.all(), "name", "employments__personality")


def occupation_roles():
    return _top(OccupationRole.objects.all(), "title", "employments__personality")


def seniority_levels():
    """Every level, not just the top ten -- the taxonomy is nine values wide."""
    rows = (
        OccupationLevel.objects.annotate(
            count=Count("employment_links__employment", distinct=True)
        )
        .order_by("-count", "title")
        .values_list("title", "count")
    )
    return [{"name": title, "count": count} for title, count in rows]


def seniority_by_role():
    """Level x function cross-tab, the one pairing where both axes are clean.

    Returned long rather than wide so a caller can pivot it however it likes.
    """
    rows = (
        EmploymentLevel.objects.filter(
            employment__personality__deleted_at__isnull=True,
            employment__occupation_role__isnull=False,
        )
        .values(
            role=F("employment__occupation_role__title"),
            level=F("occupation_level__title"),
        )
        .annotate(count=Count("employment_id", distinct=True))
        .order_by("-count", "role", "level")
    )
    return [
        {"role": row["role"], "level": row["level"], "count": row["count"]}
        for row in rows
    ]


def company_sizes():
    rows = dict(
        Company.objects.filter(size__in=COMPANY_SIZE_BUCKETS)
        .values_list("size")
        .annotate(count=Count("id"))
    )
    return [
        {"name": bucket, "count": rows.get(bucket, 0)} for bucket in COMPANY_SIZE_BUCKETS
    ]


def _tenure_years():
    """Completed stints as a fractional-year expression, computed in the database."""
    return _employments().filter(
        start_date__isnull=False,
        end_date__isnull=False,
        end_date__gte=F("start_date"),
    )


def tenure():
    span = ExpressionWrapper(
        F("end_date") - F("start_date"), output_field=DurationField()
    )
    qs = _tenure_years().annotate(span=span)

    # Buckets are folded into the same aggregate as the summary, so the whole
    # panel costs one query rather than one per bar.
    bucket_counts = {}
    for label, low, high in TENURE_BUCKETS:
        condition = Q()
        if low is not None:
            condition &= Q(span__gte=_years(low))
        if high is not None:
            condition &= Q(span__lt=_years(high))
        bucket_counts[_bucket_key(label)] = Count("id", filter=condition)

    summary = qs.aggregate(
        sample_size=Count("id"),
        mean=Avg("span"),
        median=Median("span", output_field=DurationField()),
        **bucket_counts,
    )

    return {
        "sample_size": summary["sample_size"],
        "mean_years": _to_years(summary["mean"]),
        "median_years": _to_years(summary["median"]),
        "buckets": [
            {"name": label, "count": summary[_bucket_key(label)]}
            for label, _, _ in TENURE_BUCKETS
        ],
    }


def _bucket_key(label):
    """Aggregate aliases must be identifiers; bucket labels are prose."""
    return "bucket_" + label.replace(" ", "_").replace("+", "plus").replace("-", "_")


def _years(value):
    return timedelta(days=value * 365.25)


def _to_years(delta):
    if delta is None:
        return None
    return round(delta.days / 365.25, 1)


def employment_status():
    qs = _employments()
    current = qs.filter(is_current=True).count()
    return [
        {"name": "current", "count": current},
        {"name": "past", "count": qs.count() - current},
    ]


def employments_per_person():
    """How many roles each profile carries -- the histogram, not the raw list."""
    counts = (
        _personalities()
        .annotate(n=Count("employments"))
        .values_list("n", flat=True)
    )
    histogram = {}
    for n in counts:
        histogram[n] = histogram.get(n, 0) + 1
    return [
        {"employments": n, "people": people}
        for n, people in sorted(histogram.items())
    ]


def hires_by_year():
    """Employment start years -- the only real time axis in the dataset.

    ``created_at`` would only ever plot the day the import ran.
    """
    rows = (
        _employments()
        .filter(start_date__isnull=False)
        .annotate(year=ExtractYear("start_date"))
        .values("year")
        .annotate(count=Count("id"))
        .order_by("year")
    )
    return [{"year": row["year"], "count": row["count"]} for row in rows]


def social_platforms():
    rows = (
        SocialPlatform.objects.annotate(
            profiles=Count("socialprofiles", distinct=True),
            people=Count("socialprofiles__personality", distinct=True),
        )
        .order_by("-profiles", "slug")
        .values_list("slug", "profiles", "people")
    )
    return [
        {"name": slug, "profiles": profiles, "people": people}
        for slug, profiles, people in rows
    ]


def platform_reach():
    """People grouped by how many distinct platforms they were found on."""
    counts = (
        _personalities()
        .annotate(n=Count("socialprofiles__social_platform", distinct=True))
        .values_list("n", flat=True)
    )
    histogram = {}
    for n in counts:
        histogram[n] = histogram.get(n, 0) + 1
    return [
        {"platforms": n, "people": people} for n, people in sorted(histogram.items())
    ]


def coverage():
    """Fill rate per profile field, so the gaps are visible instead of implied."""
    total = _personalities().count()
    if not total:
        return []

    filled = _personalities().aggregate(
        **{
            field: Count("id", filter=Q(**{f"{field}__isnull": False}))
            for field in COVERAGE_FIELDS
        }
    )
    return [
        {
            "name": field,
            "filled": filled[field],
            "total": total,
            "percent": round(filled[field] * 100 / total, 1),
        }
        for field in COVERAGE_FIELDS
    ]


def imports():
    """Pipeline health, straight off the batch counters the workers maintain."""
    rows = (
        ImportBatch.objects.values("status")
        .annotate(count=Count("id"))
        .order_by("-count", "status")
    )
    rolled_up = ImportBatch.objects.aggregate(
        processed_rows=Sum("processed_rows"),
        created_rows=Sum("created_rows"),
        updated_rows=Sum("updated_rows"),
        failed_rows=Sum("failed_rows"),
    )
    return {
        "batches": [{"name": row["status"], "count": row["count"]} for row in rows],
        **{field: value or 0 for field, value in rolled_up.items()},
    }


def link_totals():
    """Row counts for the join tables, which size the attribute panels."""
    return {
        "personality_skills": PersonalitySkill.objects.count(),
        "personality_interests": PersonalityInterest.objects.count(),
        "personality_languages": PersonalityLanguage.objects.count(),
        "personality_certifications": PersonalityCertification.objects.count(),
    }


def dashboard_stats():
    """The whole snapshot, assembled in one place so the view stays trivial."""
    return {
        "totals": {**totals(), **link_totals()},
        "gender": gender_split(),
        "top_skills": top_skills(),
        "top_interests": top_interests(),
        "top_languages": top_languages(),
        "top_certifications": top_certifications(),
        "top_companies": top_companies(),
        "company_sizes": company_sizes(),
        "occupation_roles": occupation_roles(),
        "seniority_levels": seniority_levels(),
        "seniority_by_role": seniority_by_role(),
        "tenure": tenure(),
        "employment_status": employment_status(),
        "employments_per_person": employments_per_person(),
        "hires_by_year": hires_by_year(),
        "social_platforms": social_platforms(),
        "platform_reach": platform_reach(),
        "coverage": coverage(),
        "imports": imports(),
    }

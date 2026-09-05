"""Turning one parsed CSV row into the normalised tables.

Everything here is written to be re-runnable. Each row is keyed by its source
identifier and upserted, joins are inserted with ``ignore_conflicts``, and lookups
lean on the database's unique constraints rather than trying to win a read-then-
write race against sibling workers. Importing the same file twice is therefore a
no-op rather than a duplicate.

The employment history comes from the nested ``experience`` cell, which already
contains the current job flagged as ``is_primary``; the flat ``job_*`` columns are
a denormalised copy of that same entry and are used only when ``experience`` is
empty.
"""

import random
import time
from dataclasses import dataclass, field

from django.db import IntegrityError, OperationalError, transaction

from social_api.models import (
    Company,
    CompanySocialProfiles,
    Employment,
    EmploymentLevel,
    Location,
    OccupationSubRole,
    Personality,
    PersonalityCertification,
    PersonalityInterest,
    PersonalityLanguage,
    PersonalityLocation,
    PersonalitySkill,
    SocialPlatform,
    SocialProfiles,
)
from social_api.models.enums import GenderType
from social_api.services.imports import parsing
from social_api.services.imports.references import References
from social_api.services.slug import build_slug

# Columns that can identify a profile across imports, best first.
IDENTITY_COLUMNS = ("linkedin_id", "linkedin_username")

PLATFORM_DOMAINS = {
    "linkedin": "linkedin.com",
    "facebook": "facebook.com",
    "twitter": "twitter.com",
    "github": "github.com",
}

# Flat columns that mirror a networks's profile when ``profiles`` is missing it.
FLAT_PROFILE_COLUMNS = {
    "linkedin": ("linkedin_id", "linkedin_username", "linkedin_url"),
    "facebook": ("facebook_id", "facebook_username", "facebook_url"),
    "twitter": (None, "twitter_username", "twitter_url"),
    "github": (None, "github_username", "github_url"),
}

MAX_PROFICIENCY = 5

# Serialization failure and deadlock. Postgres resolves a deadlock by aborting one
# transaction and expects the application to try again, so these are outcomes to
# retry rather than defects to report.
RETRYABLE_SQLSTATES = frozenset({"40001", "40P01"})
DEADLOCK_ATTEMPTS = 4
DEADLOCK_BACKOFF_SECONDS = 0.05


@dataclass
class ChunkResult:
    """What one chunk did, folded back into the batch counters."""

    created: int = 0
    updated: int = 0
    errors: list = field(default_factory=list)  # (row_number, message, excerpt)

    @property
    def failed(self) -> int:
        return len(self.errors)

    @property
    def processed(self) -> int:
        return self.created + self.updated + self.failed


class ChunkImporter:
    """Persists the rows of a single chunk.

    Lookup tables are warmed once for the whole chunk before any row is written,
    which is what turns hundreds of per-row ``get_or_create`` calls into one bulk
    insert plus one read per table.
    """

    def __init__(self, batch):
        self.batch = batch
        self.references = References()
        self._locations = {}
        self._companies = {}
        self._platforms = {}

    def run(self, rows) -> ChunkResult:
        rows = list(rows)
        self._warm([row.values for row in rows if row.ok])

        result = ChunkResult()
        for row in rows:
            if not row.ok:
                result.errors.append((row.number, row.error, row.excerpt))
                continue
            try:
                created = self._import_with_retries(row.values)
            except Exception as exc:  # noqa: BLE001 - one bad row, not a bad chunk
                result.errors.append(
                    (row.number, f"{type(exc).__name__}: {exc}"[:1000], row.excerpt)
                )
            else:
                if created:
                    result.created += 1
                else:
                    result.updated += 1
        return result

    def _import_with_retries(self, values) -> bool:
        """Import one row, giving way and retrying when a sibling worker wins.

        Each row gets its own savepoint. The chunk runs in a single transaction so
        that a task retry is all-or-nothing, but one malformed profile must not
        poison the rows around it -- and a deadlock, which is routine when several
        chunks upsert the same companies and lookup rows, must not cost a profile
        that would import perfectly well a moment later.
        """
        for attempt in range(DEADLOCK_ATTEMPTS):
            try:
                with transaction.atomic():
                    return self.import_row(values)
            except OperationalError as exc:
                if attempt == DEADLOCK_ATTEMPTS - 1 or not _is_retryable(exc):
                    raise
                # Jittered, so the losers of one pile-up do not collide again.
                time.sleep(DEADLOCK_BACKOFF_SECONDS * (attempt + 1) * (0.5 + random.random()))
        raise AssertionError("unreachable")  # pragma: no cover

    # -- reference warming ------------------------------------------------

    def _warm(self, rows):
        industries, skills, interests = set(), set(), set()
        languages, certifications = set(), set()
        titles, roles, levels = set(), set(), set()
        certification_extras = {}

        for values in rows:
            industries.add(parsing.text(values.get("industry")))
            industries.add(parsing.text(values.get("job_company_industry")))
            skills.update(parsing.string_list(values.get("skills")))
            interests.update(parsing.string_list(values.get("interests")))
            levels.update(parsing.string_list(values.get("job_title_levels")))

            for entry in parsing.dict_list(values.get("languages")):
                languages.add(parsing.text(entry.get("name")))

            for entry in parsing.dict_list(values.get("certifications")):
                name = parsing.text(entry.get("name"))
                if not name:
                    continue
                certifications.add(name)
                organization = parsing.text(entry.get("organization"), max_length=255)
                if organization:
                    certification_extras[name] = {"organization": organization}

            for entry in self._experience_entries(values):
                title = entry.get("title") or {}
                titles.add(parsing.text(title.get("name")))
                roles.add(parsing.text(title.get("role")))
                levels.update(
                    parsing.text(level) for level in (title.get("levels") or [])
                )
                company = entry.get("company") or {}
                industries.add(parsing.text(company.get("industry")))

        self.references.industries.warm(_present(industries))
        self.references.skills.warm(_present(skills))
        self.references.interests.warm(_present(interests))
        self.references.languages.warm(_present(languages))
        self.references.certifications.warm(
            _present(certifications), extras=certification_extras
        )
        self.references.occupations.warm(_present(titles))
        self.references.occupation_roles.warm(_present(roles))
        self.references.occupation_levels.warm(_present(levels))

    # -- row ---------------------------------------------------------------

    def import_row(self, values) -> bool:
        """Upsert one profile and everything hanging off it. Returns ``created``."""
        personality, created = self._personality(values)
        self._sync_locations(personality, values)
        self._sync_attributes(personality, values)
        self._sync_employments(personality, values)
        self._sync_profiles(personality, values)
        return created

    def _personality(self, values):
        first_name, last_name = self._names(values)
        if not first_name and not last_name:
            raise ValueError("row carries no usable name")

        middle_initial = parsing.text(values.get("middle_initial"))
        defaults = {
            "import_batch": self.batch,
            "industry": self.references.industries.get(
                parsing.text(values.get("industry"))
            ),
            "first_name": first_name,
            "middle_name": parsing.text(values.get("middle_name"), max_length=255),
            "middle_initial": middle_initial[:1] if middle_initial else None,
            "last_name": last_name,
            "gender": self._gender(values.get("gender")),
            "birth_date": parsing.date(values.get("birth_date")),
            "birth_year": parsing.year(values.get("birth_year")),
            "summary": parsing.text(values.get("summary")),
            "inferred_salary": parsing.text(
                values.get("inferred_salary"), max_length=100
            ),
            "inferred_years_experience": parsing.small_integer(
                values.get("inferred_years_experience")
            ),
            "version_status": parsing.mapping(values.get("version_status")),
            "location_last_updated": parsing.date(values.get("location_last_updated")),
        }

        external_id = _identity(values)
        if external_id:
            return Personality.objects.update_or_create(
                external_id=external_id, defaults=defaults
            )
        # No stable identifier in the source: the row can only ever be inserted.
        return Personality.objects.create(**defaults), True

    def _names(self, values):
        first_name = parsing.text(values.get("first_name"), max_length=255)
        last_name = parsing.text(values.get("last_name"), max_length=255)
        if first_name or last_name:
            return first_name or "", last_name or ""

        full_name = parsing.text(values.get("full_name"), max_length=255)
        if not full_name:
            return "", ""
        head, _, tail = full_name.partition(" ")
        return head, tail

    def _gender(self, raw):
        value = (parsing.text(raw) or "").lower()
        return value if value in GenderType.values else GenderType.UNKNOWN

    # -- locations ----------------------------------------------------------

    def _sync_locations(self, personality, values):
        primary = self._location(
            {
                "locality": values.get("location_locality"),
                "metro": values.get("location_metro"),
                "region": values.get("location_region"),
                "country": values.get("location_country"),
                "continent": values.get("location_continent"),
                "geo": values.get("location_geo"),
            }
        )
        if primary is not None:
            self._link_location(
                personality,
                primary,
                street_address=parsing.text(
                    values.get("location_street_address"), max_length=255
                ),
                postal_code=parsing.text(
                    values.get("location_postal_code"), max_length=20
                ),
                is_primary=True,
            )

        for entry in parsing.dict_list(values.get("street_addresses")):
            location = self._location(entry)
            if location is None:
                continue
            self._link_location(
                personality,
                location,
                street_address=parsing.text(
                    entry.get("street_address"), max_length=255
                ),
                postal_code=parsing.text(entry.get("postal_code"), max_length=20),
                is_primary=False,
            )

    def _link_location(self, personality, location, *, street_address, postal_code, is_primary):
        link, created = PersonalityLocation.objects.get_or_create(
            personality=personality,
            location=location,
            street_address=street_address,
            defaults={"postal_code": postal_code, "is_primary": is_primary},
        )
        if not created and is_primary and not link.is_primary:
            link.is_primary = True
            link.save(update_fields=["is_primary", "updated_at"])

    def _location(self, data):
        locality = parsing.text(data.get("locality"), max_length=126)
        region = parsing.text(data.get("region"), max_length=126)
        country = parsing.text(data.get("country"), max_length=126)
        if not any((locality, region, country)):
            return None

        key = (locality, region, country)
        if key in self._locations:
            return self._locations[key]

        latitude, longitude = parsing.coordinates(data.get("geo"))
        location, _ = Location.objects.get_or_create(
            locality=locality,
            region=region,
            country=country,
            defaults={
                "name": _granularity(locality, region),
                "metro": parsing.text(data.get("metro"), max_length=126),
                "continent": parsing.text(data.get("continent"), max_length=126),
                "latitude": latitude,
                "longitude": longitude,
            },
        )
        self._locations[key] = location
        return location

    # -- attributes ---------------------------------------------------------

    def _sync_attributes(self, personality, values):
        # Rows are inserted in primary-key order here and in every other bulk
        # insert below. Workers contend for the same skill and interest rows
        # constantly, and taking their locks in a consistent order is what stops
        # two chunks from deadlocking against each other.
        skills = self.references.skills.get_many(
            parsing.string_list(values.get("skills"))
        )
        PersonalitySkill.objects.bulk_create(
            [
                PersonalitySkill(personality=personality, skill=skill)
                for skill in sorted(skills, key=_by_pk)
            ],
            ignore_conflicts=True,
        )

        interests = self.references.interests.get_many(
            parsing.string_list(values.get("interests"))
        )
        PersonalityInterest.objects.bulk_create(
            [
                PersonalityInterest(personality=personality, interest=interest)
                for interest in sorted(interests, key=_by_pk)
            ],
            ignore_conflicts=True,
        )

        self._sync_languages(personality, values)
        self._sync_certifications(personality, values)

    def _sync_languages(self, personality, values):
        links = {}
        for entry in parsing.dict_list(values.get("languages")):
            language = self.references.languages.get(parsing.text(entry.get("name")))
            if language is None or language.pk in links:
                continue
            proficiency = parsing.integer(entry.get("proficiency"))
            if proficiency is not None and not 0 <= proficiency <= MAX_PROFICIENCY:
                proficiency = None
            links[language.pk] = PersonalityLanguage(
                personality=personality, language=language, proficiency=proficiency
            )
        PersonalityLanguage.objects.bulk_create(
            [links[key] for key in sorted(links)], ignore_conflicts=True
        )

    def _sync_certifications(self, personality, values):
        links = {}
        for entry in parsing.dict_list(values.get("certifications")):
            certification = self.references.certifications.get(
                parsing.text(entry.get("name"))
            )
            if certification is None:
                continue
            start_date = parsing.date(entry.get("start_date"))
            key = (certification.pk, start_date)
            if key in links:
                continue
            links[key] = PersonalityCertification(
                personality=personality,
                certification=certification,
                start_date=start_date,
                end_date=parsing.date(entry.get("end_date")),
            )
        PersonalityCertification.objects.bulk_create(
            [links[key] for key in sorted(links, key=lambda item: item[0])],
            ignore_conflicts=True,
        )

    # -- employment ---------------------------------------------------------

    def _sync_employments(self, personality, values):
        last_updated = parsing.date(values.get("job_last_updated"))
        for entry in self._experience_entries(values):
            self._employment(
                personality,
                entry,
                last_updated=last_updated if entry.get("is_primary") else None,
            )

    def _experience_entries(self, values):
        entries = parsing.dict_list(values.get("experience"))
        if entries:
            return entries
        fallback = self._flat_experience(values)
        return [fallback] if fallback else []

    def _flat_experience(self, values):
        """Rebuild an ``experience`` entry from the denormalised ``job_*`` columns."""
        if not parsing.text(values.get("job_title")):
            return None
        return {
            "is_primary": True,
            "start_date": values.get("job_start_date"),
            "end_date": None,
            "summary": values.get("job_summary"),
            "title": {
                "name": values.get("job_title"),
                "role": values.get("job_title_role"),
                "sub_role": values.get("job_title_sub_role"),
                "levels": parsing.string_list(values.get("job_title_levels")),
            },
            "company": {
                "id": values.get("job_company_id"),
                "name": values.get("job_company_name"),
                "website": values.get("job_company_website"),
                "size": values.get("job_company_size"),
                "founded": values.get("job_company_founded"),
                "industry": values.get("job_company_industry"),
                "linkedin_url": values.get("job_company_linkedin_url"),
                "facebook_url": values.get("job_company_facebook_url"),
                "twitter_url": values.get("job_company_twitter_url"),
                "location": {
                    "locality": values.get("job_company_location_locality"),
                    "metro": values.get("job_company_location_metro"),
                    "region": values.get("job_company_location_region"),
                    "country": values.get("job_company_location_country"),
                    "continent": values.get("job_company_location_continent"),
                    "geo": values.get("job_company_location_geo"),
                    "street_address": values.get(
                        "job_company_location_street_address"
                    ),
                    "postal_code": values.get("job_company_location_postal_code"),
                    "address_line_2": values.get(
                        "job_company_location_address_line_2"
                    ),
                },
            },
        }

    def _employment(self, personality, entry, *, last_updated=None):
        title_data = entry.get("title") or {}
        title = parsing.text(title_data.get("name"), max_length=255)
        if not title:
            return

        company = self._company(entry.get("company") or {})
        role = self.references.occupation_roles.get(parsing.text(title_data.get("role")))
        start_date = parsing.date(entry.get("start_date"))
        end_date = parsing.date(entry.get("end_date"))

        employment, _ = Employment.objects.update_or_create(
            personality=personality,
            company=company,
            title=title,
            start_date=start_date,
            defaults={
                "occupation": self.references.occupations.get(title),
                "occupation_role": role,
                "occupation_sub_role": self._sub_role(
                    role, parsing.text(title_data.get("sub_role"))
                ),
                "location": company.location if company else None,
                "summary": parsing.text(entry.get("summary")),
                "end_date": end_date,
                "is_current": bool(entry.get("is_primary")) or end_date is None,
                "last_updated": last_updated,
            },
        )

        levels = self.references.occupation_levels.get_many(
            [parsing.text(level) for level in (title_data.get("levels") or [])]
        )
        EmploymentLevel.objects.bulk_create(
            [
                EmploymentLevel(employment=employment, occupation_level=level)
                for level in sorted(levels, key=_by_pk)
            ],
            ignore_conflicts=True,
        )

    def _sub_role(self, role, title):
        if role is None or not title:
            return None
        try:
            slug = build_slug(title, max_length=255)
        except ValueError:
            return None
        sub_role, _ = OccupationSubRole.objects.get_or_create(
            occupation_role=role,
            slug=slug,
            defaults={"title": title[:255]},
        )
        return sub_role

    # -- companies ----------------------------------------------------------

    def _company(self, data):
        external_id = parsing.text(data.get("id"), max_length=255)
        name = parsing.text(data.get("name"), max_length=255)
        if not name:
            return None

        key = external_id or f"name:{name.lower()}"
        if key in self._companies:
            return self._companies[key]

        location_data = data.get("location") or {}
        defaults = {
            "name": name,
            "industry": self.references.industries.get(
                parsing.text(data.get("industry"))
            ),
            "website": _normalise_url(data.get("website")),
            "size": parsing.text(data.get("size"), max_length=50),
            "founded_year": parsing.year(data.get("founded")),
            "location": self._location(location_data),
            "street_address": parsing.text(
                location_data.get("street_address"), max_length=255
            ),
            "address_line_2": parsing.text(
                location_data.get("address_line_2"), max_length=255
            ),
            "postal_code": parsing.text(
                location_data.get("postal_code"), max_length=20
            ),
        }

        company = self._get_or_create_company(external_id, name, defaults)
        self._companies[key] = company
        if company is not None:
            self._sync_company_profiles(company, data)
        return company

    def _get_or_create_company(self, external_id, name, defaults):
        lookup = (
            {"external_id": external_id}
            if external_id
            else {"name": name, "external_id__isnull": True}
        )
        existing = Company.objects.filter(**lookup).order_by("id").first()
        if existing is not None:
            return existing
        try:
            with transaction.atomic():
                return Company.objects.create(external_id=external_id, **defaults)
        except IntegrityError:
            # A sibling worker inserted the same company between our read and our
            # write, or won the race for the slug. The unique constraints are the
            # real guarantee -- Company.save()'s slug lookup is read-then-write and
            # cannot be one -- so re-read rather than retry the insert.
            return Company.objects.filter(**lookup).order_by("id").first()

    def _sync_company_profiles(self, company, data):
        for network in ("linkedin", "facebook", "twitter"):
            url = _normalise_url(data.get(f"{network}_url"))
            if not url:
                continue
            platform = self._platform(network)
            if platform is None:
                continue
            try:
                with transaction.atomic():
                    CompanySocialProfiles.objects.update_or_create(
                        social_platform=platform,
                        company=company,
                        defaults={
                            "platform_user_id": parsing.text(
                                data.get(f"{network}_id"), max_length=255
                            ),
                            "url": url,
                        },
                    )
            except IntegrityError:
                continue

    # -- social profiles ----------------------------------------------------

    def _sync_profiles(self, personality, values):
        connections = parsing.standard_integer(values.get("linkedin_connections"))
        seen = set()

        for entry in parsing.dict_list(values.get("profiles")):
            network = (parsing.text(entry.get("network")) or "").lower()
            if not network:
                continue
            seen.add(network)
            self._link_profile(
                personality,
                network,
                platform_user_id=parsing.text(entry.get("id"), max_length=255),
                username=parsing.text(entry.get("username"), max_length=255),
                url=_normalise_url(entry.get("url")),
                connections=connections if network == "linkedin" else None,
            )

        # Networks that only appear as flat columns still deserve a row.
        for network, (id_column, username_column, url_column) in FLAT_PROFILE_COLUMNS.items():
            if network in seen:
                continue
            self._link_profile(
                personality,
                network,
                platform_user_id=parsing.text(
                    values.get(id_column), max_length=255
                )
                if id_column
                else None,
                username=parsing.text(values.get(username_column), max_length=255),
                url=_normalise_url(values.get(url_column)),
                connections=connections if network == "linkedin" else None,
            )

    def _link_profile(self, personality, network, *, platform_user_id, username, url, connections):
        if not platform_user_id and not username:
            return
        platform = self._platform(network)
        if platform is None:
            return

        # Both (platform, platform_user_id) and (platform, user_name) are unique,
        # so match on whichever the source actually gave us.
        lookup = (
            {"social_platform": platform, "platform_user_id": platform_user_id}
            if platform_user_id
            else {"social_platform": platform, "user_name": username}
        )
        try:
            with transaction.atomic():
                SocialProfiles.objects.update_or_create(
                    **lookup,
                    defaults={
                        "personality": personality,
                        "user_name": username,
                        "url": url,
                        "connection_count": connections,
                    },
                )
        except IntegrityError:
            # The other unique key already points somewhere else; keep the
            # existing row rather than failing the profile.
            return

    def _platform(self, network):
        network = (network or "").lower()
        if network in self._platforms:
            return self._platforms[network]
        try:
            slug = build_slug(network, max_length=255)
        except ValueError:
            return None
        platform, _ = SocialPlatform.objects.get_or_create(
            slug=slug,
            defaults={
                "name": network.title(),
                "domain": PLATFORM_DOMAINS.get(slug, f"{slug}.com"),
            },
        )
        self._platforms[network] = platform
        return platform


def _is_retryable(exc):
    """True for the wire errors Postgres expects the client to retry."""
    return getattr(exc.__cause__, "sqlstate", None) in RETRYABLE_SQLSTATES


def _by_pk(row):
    return row.pk


def _identity(values):
    for column in IDENTITY_COLUMNS:
        found = parsing.text(values.get(column), max_length=255)
        if found:
            return found
    return None


def _granularity(locality, region):
    if locality:
        return Location.LocationName.CITY
    if region:
        return Location.LocationName.REGION
    return Location.LocationName.COUNTRY


def _normalise_url(value):
    url = parsing.text(value, max_length=255)
    if not url:
        return None
    if "://" not in url:
        url = f"https://{url}"
    return url[:255]


def _present(values):
    return [value for value in values if value]

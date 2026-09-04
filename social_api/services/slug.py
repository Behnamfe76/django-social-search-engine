"""Slug building helpers.

``build_slug`` is the plain "slugify this text" entry point. ``build_unique_slug``
adds a numeric suffix until the slug is free for a given model field, which is what
unique slug columns such as ``Company.slug`` need.
"""

import itertools

from django.utils.text import slugify

SEPARATOR = "-"

# Room left at the end of a max-length slug for a "-99999" style suffix.
SUFFIX_RESERVE = 6

MAX_ATTEMPTS = 100_000


def build_slug(value, *, max_length=None, allow_unicode=False, fallback=None):
    """Slugify ``value``, optionally truncated to ``max_length``.

    Truncation never leaves a dangling separator, so a slug cut mid-word ends on a
    word boundary rather than ``"acme-"``.

    Raises ``ValueError`` when ``value`` has no slug-able characters (e.g. ``"!!!"``)
    and no usable ``fallback`` was given.
    """
    slug = slugify(value or "", allow_unicode=allow_unicode)

    if not slug and fallback is not None:
        slug = slugify(fallback, allow_unicode=allow_unicode)

    if not slug:
        raise ValueError(f"Cannot build a slug from {value!r}")

    return _truncate(slug, max_length)


def build_unique_slug(
    value,
    *,
    model,
    field_name="slug",
    instance=None,
    queryset=None,
    max_length=None,
    allow_unicode=False,
    fallback=None,
):
    """Build a slug for ``value`` that no other ``model`` row already uses.

    The first free candidate wins: ``acme``, then ``acme-2``, ``acme-3``, and so on.
    ``max_length`` defaults to the model field's own ``max_length``.

    Pass ``instance`` when updating an existing row so its current slug does not
    count as a collision, or ``queryset`` to scope the search (e.g. per tenant).

    This reads before it writes, so concurrent inserts can still race; keep the
    database unique constraint as the real guarantee.
    """
    if max_length is None:
        max_length = model._meta.get_field(field_name).max_length

    slug = build_slug(
        value,
        max_length=max_length,
        allow_unicode=allow_unicode,
        fallback=fallback,
    )
    # Suffixed candidates are built off a shorter stem so they still fit max_length.
    stem = _truncate(slug, max_length - SUFFIX_RESERVE if max_length else None)

    lookup = queryset if queryset is not None else model._default_manager.all()
    if instance is not None and instance.pk is not None:
        lookup = lookup.exclude(pk=instance.pk)

    # One query: every slug that could collide shares the stem as a prefix.
    taken = set(
        lookup.filter(**{f"{field_name}__startswith": stem}).values_list(
            field_name, flat=True
        )
    )

    if slug not in taken:
        return slug

    for suffix in itertools.islice(itertools.count(2), MAX_ATTEMPTS):
        candidate = f"{stem}{SEPARATOR}{suffix}"
        if candidate not in taken:
            return candidate

    raise ValueError(f"Could not find a free slug for {value!r} after {MAX_ATTEMPTS} attempts")


def _truncate(slug, max_length):
    """Cut ``slug`` to ``max_length`` without leaving a trailing separator."""
    if not max_length or len(slug) <= max_length:
        return slug
    return slug[:max_length].rstrip(SEPARATOR) or slug[:max_length]

"""One row shape for every filter-options list."""

from rest_framework import serializers


class LookupSerializer(serializers.Serializer):
    """An option the user can filter by.

    ``id`` is what goes back as the filter value, ``name`` is what is shown, and
    ``count`` is how many profiles currently match -- enough for the front end to
    render "Software (23)" and to grey out options that would return nothing.
    """

    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    count = serializers.IntegerField(read_only=True)


class LookupRefSerializer(serializers.Serializer):
    """A lookup embedded in another payload: the label, plus the id to filter by.

    Deliberately the same ``id``/``name`` pair the lookup endpoints return, minus
    the count, so a chip rendered from a profile can be fed straight back into
    the corresponding ``?<name>_id=`` filter.
    """

    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)


class TitleRefSerializer(LookupRefSerializer):
    """Same shape for the models that spell their label ``title``."""

    name = serializers.CharField(source="title", read_only=True)

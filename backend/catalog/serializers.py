from rest_framework import serializers


class CatalogSlugField(serializers.SlugRelatedField):
    """Accept a catalog entry's slug on write and return {slug, name} on read."""

    def __init__(self, **kwargs):
        kwargs.setdefault("slug_field", "slug")
        super().__init__(**kwargs)

    def to_representation(self, obj):
        return {"slug": obj.slug, "name": obj.name}


class CatalogEntrySerializer(serializers.Serializer):
    slug = serializers.SlugField(read_only=True)
    name = serializers.CharField(read_only=True)

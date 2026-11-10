from django.db import transaction
from django.utils.text import slugify


def unique_slug(model, name):
    base = slugify(name)[:60]
    slug, suffix = base, 2
    while model.objects.filter(slug=slug).exists():
        slug = f"{base}-{suffix}"
        suffix += 1
    return slug


@transaction.atomic
def get_or_create_entry(model, name):
    """Return the entry named ``name`` (ignoring case), creating it if needed.

    Returns (entry, created).
    """
    existing = model.objects.filter(name__iexact=name).first()
    if existing is not None:
        return existing, False
    return model.objects.create(name=name, slug=unique_slug(model, name)), True

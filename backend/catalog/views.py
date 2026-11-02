from rest_framework import generics

from .models import Role, Skill
from .serializers import CatalogEntrySerializer


class SkillListView(generics.ListAPIView):
    queryset = Skill.objects.all()
    serializer_class = CatalogEntrySerializer
    pagination_class = None


class RoleListView(generics.ListAPIView):
    queryset = Role.objects.all()
    serializer_class = CatalogEntrySerializer
    pagination_class = None

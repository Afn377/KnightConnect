from rest_framework import generics

from .models import Skill
from .serializers import CatalogEntrySerializer


class SkillListView(generics.ListAPIView):
    queryset = Skill.objects.all()
    serializer_class = CatalogEntrySerializer
    pagination_class = None

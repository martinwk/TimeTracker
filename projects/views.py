from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

from .models import Project, TimeEntry, ActivityMapping
from .serializers import (
    ProjectSerializer,
    TimeEntrySerializer,
    ActivityMappingSerializer,
)


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["is_active"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]


class TimeEntryViewSet(viewsets.ModelViewSet):
    queryset = TimeEntry.objects.all()
    serializer_class = TimeEntrySerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["project", "date"]
    ordering_fields = ["date", "project__name"]
    ordering = ["-date"]


class ActivityMappingViewSet(viewsets.ModelViewSet):
    queryset = ActivityMapping.objects.all()
    serializer_class = ActivityMappingSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["activity", "time_entry", "source"]
    ordering_fields = ["created_at", "activity__started_at"]
    ordering = ["-created_at"]

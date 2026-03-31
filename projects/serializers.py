from rest_framework import serializers
from .models import Project, TimeEntry, ActivityMapping


class TimeEntrySerializer(serializers.ModelSerializer):
    duration_hours = serializers.ReadOnlyField()
    project_name = serializers.CharField(source="project.name", read_only=True)

    class Meta:
        model = TimeEntry
        fields = [
            "id",
            "project",
            "project_name",
            "date",
            "duration_minutes",
            "duration_hours",
            "notes",
            "created_at",
            "updated_at",
        ]


class ActivityMappingSerializer(serializers.ModelSerializer):
    activity_app = serializers.CharField(source="activity.app_name", read_only=True)
    activity_title = serializers.CharField(source="activity.raw_title", read_only=True)
    time_entry_project = serializers.CharField(source="time_entry.project.name", read_only=True)
    source_display = serializers.CharField(source="get_source_display", read_only=True)

    class Meta:
        model = ActivityMapping
        fields = [
            "id",
            "activity",
            "activity_app",
            "activity_title",
            "time_entry",
            "time_entry_project",
            "source",
            "source_display",
            "created_at",
        ]


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = [
            "id",
            "name",
            "color",
            "is_active",
            "notes",
            "created_at",
        ]

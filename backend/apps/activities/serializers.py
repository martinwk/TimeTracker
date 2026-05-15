from rest_framework import serializers
from apps.projects.models import Project
from .models import WindowActivity, ActivityBlock, UniqueActivity, ActivityRule


class UniqueActivitySerializer(serializers.ModelSerializer):
    total_minutes = serializers.ReadOnlyField()

    class Meta:
        model = UniqueActivity
        fields = ["id", "block", "raw_title", "total_seconds", "total_minutes"]


class ProjectInlineSerializer(serializers.ModelSerializer):
    """Minimale projectweergave voor inlining in blokresponses."""

    class Meta:
        model = Project
        fields = ["id", "name", "color"]


class ActivityBlockSerializer(serializers.ModelSerializer):
    unique_activities = UniqueActivitySerializer(many=True, read_only=True)
    total_minutes = serializers.ReadOnlyField()
    dominant_title = serializers.ReadOnlyField()
    project = ProjectInlineSerializer(read_only=True)
    project_id = serializers.PrimaryKeyRelatedField(
        source="project",
        queryset=Project.objects.all(),
        allow_null=True,
        required=False,
        write_only=True,
    )
    project_name = serializers.CharField(source="project.name", read_only=True, allow_null=True)
    suggested_projects = serializers.SerializerMethodField()

    # Optioneel bij handmatig aanmaken — defaults worden ingevuld in create()
    app_name       = serializers.CharField(required=False, max_length=255)
    activity_count = serializers.IntegerField(required=False)
    block_minutes  = serializers.IntegerField(required=False)
    ended_at       = serializers.DateTimeField(required=False)
    date           = serializers.DateField(required=False)

    class Meta:
        model = ActivityBlock
        fields = [
            "id",
            "app_name",
            "date",
            "started_at",
            "ended_at",
            "total_seconds",
            "total_minutes",
            "activity_count",
            "block_minutes",
            "dominant_title",
            "project",
            "project_id",
            "project_name",
            "suggested_projects",
            "unique_activities",
        ]

    def create(self, validated_data):
        from datetime import timedelta
        from django.utils.timezone import localdate

        started_at    = validated_data["started_at"]
        total_seconds = validated_data["total_seconds"]

        validated_data.setdefault("app_name",       "handmatig")
        validated_data.setdefault("activity_count", 1)
        validated_data.setdefault("block_minutes",  15)
        validated_data["ended_at"] = started_at + timedelta(seconds=total_seconds)
        validated_data["date"]     = localdate(started_at)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        from datetime import timedelta
        from django.utils.timezone import localdate

        instance = super().update(instance, validated_data)
        instance.ended_at = instance.started_at + timedelta(seconds=instance.total_seconds)
        instance.date = localdate(instance.started_at)
        instance.save(update_fields=["ended_at", "date"])
        return instance

    def get_suggested_projects(self, obj):
        """
        Return ranked project suggestions for this block.
        Only shown if block doesn't have a project yet.
        """
        if obj.project:
            return []
        
        suggestions = []
        
        # 1. Recent project for this app
        recent = obj.get_recent_project_for_app()
        if recent:
            suggestions.append({
                "project_id": recent.id,
                "project_name": recent.name,
                "reason": "Onlangs gebruikt voor deze app",
                "confidence": 0.8,
            })
        
        # 2. Project for dominant activity title
        dominant_proj = obj.get_project_for_dominant_activity()
        if dominant_proj and (not recent or dominant_proj.id != recent.id):
            suggestions.append({
                "project_id": dominant_proj.id,
                "project_name": dominant_proj.name,
                "reason": "Gebruikt voor deze activiteit titel",
                "confidence": 0.6,
            })
        
        return suggestions


class WindowActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = WindowActivity
        fields = [
            "id",
            "started_at",
            "ended_at",
            "duration_seconds",
            "raw_title",
            "app_name",
            "date",
            "is_noise",
            "unique_activity",
        ]


class ActivityRuleSerializer(serializers.ModelSerializer):
    match_field_display = serializers.CharField(source="get_match_field_display", read_only=True)

    class Meta:
        model = ActivityRule
        fields = [
            "id",
            "project",
            "match_field",
            "match_field_display",
            "match_value",
            "priority",
            "is_active",
            "created_at",
        ]

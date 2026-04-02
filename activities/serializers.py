from rest_framework import serializers
from .models import WindowActivity, ActivityBlock, UniqueActivity, ActivityRule


class UniqueActivitySerializer(serializers.ModelSerializer):
    total_minutes = serializers.ReadOnlyField()

    class Meta:
        model = UniqueActivity
        fields = ["id", "block", "raw_title", "total_seconds", "total_minutes"]


class ActivityBlockSerializer(serializers.ModelSerializer):
    unique_activities = UniqueActivitySerializer(many=True, read_only=True)
    total_minutes = serializers.ReadOnlyField()
    dominant_title = serializers.ReadOnlyField()
    project_name = serializers.CharField(source="project.name", read_only=True, allow_null=True)
    suggested_projects = serializers.SerializerMethodField()

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
            "project_name",
            "suggested_projects",
            "unique_activities",
        ]

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

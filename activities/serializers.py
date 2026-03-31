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
            "unique_activities",
        ]


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

from django.contrib import admin
from .models import WindowActivity, ActivityRule


@admin.register(WindowActivity)
class WindowActivityAdmin(admin.ModelAdmin):
    list_display = ["started_at", "app_name", "raw_title_short", "duration_seconds", "is_noise"]
    list_filter = ["is_noise", "date", "app_name"]
    search_fields = ["raw_title", "app_name"]
    date_hierarchy = "date"
    list_editable = ["is_noise"]
    readonly_fields = ["started_at", "ended_at", "duration_seconds", "raw_title", "app_name", "date"]

    @admin.display(description="Titel (ingekort)")
    def raw_title_short(self, obj):
        return obj.raw_title[:80]


@admin.register(ActivityRule)
class ActivityRuleAdmin(admin.ModelAdmin):
    list_display = ["priority", "project", "match_field", "match_value", "is_active"]
    list_display_links = ["project"]
    list_filter = ["is_active", "match_field", "project"]
    list_editable = ["priority", "is_active"]
    ordering = ["priority"]

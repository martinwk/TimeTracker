from django.contrib import admin
from .models import Project, TimeEntry, ActivityMapping


class TimeEntryInline(admin.TabularInline):
    model = TimeEntry
    extra = 0
    fields = ["date", "duration_minutes", "notes"]
    ordering = ["-date"]


class ActivityRuleInline(admin.TabularInline):
    # Importeer vanuit activities om circulaire imports te vermijden
    from activities.models import ActivityRule
    model = ActivityRule
    extra = 1
    fields = ["priority", "match_field", "match_value", "is_active"]


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["name", "color", "is_active", "created_at"]
    list_filter = ["is_active"]
    list_editable = ["is_active"]
    inlines = [ActivityRuleInline, TimeEntryInline]


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = ["date", "project", "duration_minutes", "duration_hours", "notes_short"]
    list_filter = ["project", "date"]
    date_hierarchy = "date"
    search_fields = ["notes", "project__name"]

    @admin.display(description="Uren")
    def duration_hours(self, obj):
        return f"{obj.duration_hours:.2f}u"

    @admin.display(description="Notities")
    def notes_short(self, obj):
        return obj.notes[:60] if obj.notes else "—"


@admin.register(ActivityMapping)
class ActivityMappingAdmin(admin.ModelAdmin):
    list_display = ["activity", "time_entry", "source", "created_at"]
    list_filter = ["source", "time_entry__project"]
    raw_id_fields = ["activity", "time_entry"]

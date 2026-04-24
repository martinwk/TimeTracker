from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import WindowActivity, ActivityRule, ActivityBlock, UniqueActivity, BlockProjectHistory


# class WindowActivityInline(admin.TabularInline):
#     model = WindowActivity
#     extra = 0
#     fields = ["started_at", "ended_at", "app_name", "raw_title", "duration_seconds", "is_noise"]
#     readonly_fields = ["started_at", "ended_at", "app_name", "raw_title", "duration_seconds"]
#     ordering = ["-started_at"]

    # def edit_link(self, obj):
    #     if obj.pk:
    #         url = reverse(
    #             # f"admin:{obj._meta.app_label}_{obj._meta.model_name}_change",
    #             "admin:activities_windowactivity_change",
    #         )
    #         return format_html('<a href="{}">Details</a>', url)
    #     return ""

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
    list_display = ["priority", "project", "match_field_display", "match_value", "is_active"]
    list_display_links = ["project"]
    list_filter = ["is_active", "match_field", "project"]
    list_editable = ["priority", "is_active"]
    ordering = ["priority"]
    
    def match_field_display(self, obj):
        return obj.get_match_field_display()
    match_field_display.short_description = "Match type"

class UniqueActivityInline(admin.TabularInline):
    model = UniqueActivity
    extra = 0
    fields = ["raw_title", "total_seconds", "edit_link"]
    readonly_fields = ["raw_title", "total_seconds", "edit_link"]

    def edit_link(self, obj):
        if obj.pk:
            url = reverse("admin:activities_uniqueactivity_change", args=[obj.pk])
            return format_html('<a href="{}">Details</a>', url)
        return ""


class BlockProjectHistoryInline(admin.TabularInline):
    model = BlockProjectHistory
    extra = 0
    fields = ["project", "assigned_at", "assigned_by"]
    readonly_fields = ["project", "assigned_at", "assigned_by"]
    can_delete = False
    ordering = ["-assigned_at"]


@admin.register(ActivityBlock)
class ActivityBlockAdmin(admin.ModelAdmin):
    list_display = ["date", "app_name", "started_at", "ended_at", "total_minutes", "project", "activity_count", "block_minutes", "dominant_title_short"]
    inlines = [UniqueActivityInline, BlockProjectHistoryInline]
    list_filter = ["date", "app_name", "project"]
    search_fields = ["dominant_title", "project__name"]
    date_hierarchy = "date"
    readonly_fields = ["date", "app_name", "dominant_title", "started_at", "ended_at", "total_seconds", "activity_count"]
    list_editable = ["project"]
    actions = ["assign_project_bulk"]

    @admin.display(description="Dominante titel (ingekort)")
    def dominant_title_short(self, obj):
        return obj.dominant_title[:80]

    def assign_project_bulk(self, request, queryset):
        """
        Bulk assignment action - requires extra page to select project.
        For now, just a placeholder. A more sophisticated approach would use
        a custom form, but for MVP we'll keep it simple.
        """
        self.message_user(request, f"Selecteer blocks en kies project uit de editor.")
    assign_project_bulk.short_description = "Projecten toewijzen aan geselecteerde blokken"

@admin.register(UniqueActivity)
class UniqueActivityAdmin(admin.ModelAdmin):
    list_display = ["block", "raw_title_short", "total_minutes"]
    list_filter = ["block__date", "block__app_name"]
    search_fields = ["raw_title", "block__app_name", "block__date", "block__started_at"]
    readonly_fields = ["block", "raw_title", "total_seconds",]

    @admin.display(description="Titel (ingekort)")
    def raw_title_short(self, obj):
        return obj.raw_title[:80]


@admin.register(BlockProjectHistory)
class BlockProjectHistoryAdmin(admin.ModelAdmin):
    list_display = ["block_summary", "project", "assigned_at", "assigned_by"]
    list_filter = ["assigned_at", "assigned_by", "project"]
    search_fields = ["block__app_name", "project__name"]
    date_hierarchy = "assigned_at"
    readonly_fields = ["block", "project", "assigned_at", "assigned_by"]
    ordering = ["-assigned_at"]
    
    def block_summary(self, obj):
        return f"{obj.block.date} | {obj.block.app_name}"
    block_summary.short_description = "Block"

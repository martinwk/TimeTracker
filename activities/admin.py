from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import WindowActivity, ActivityRule, ActivityBlock, UniqueActivity


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
    list_display = ["priority", "project", "match_field", "match_value", "is_active"]
    list_display_links = ["project"]
    list_filter = ["is_active", "match_field", "project"]
    list_editable = ["priority", "is_active"]
    ordering = ["priority"]

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

@admin.register(ActivityBlock)
class ActivityBlockAdmin(admin.ModelAdmin):
    list_display = ["date", "app_name", "started_at", "ended_at", "total_minutes", "activity_count", "block_minutes", "dominant_title_short"]
    inlines = [UniqueActivityInline]
    list_filter = ["date", "app_name"]
    search_fields = ["dominant_title"]
    date_hierarchy = "date"
    readonly_fields = ["date", "app_name", "dominant_title", "started_at", "ended_at", "total_seconds", "activity_count"]

    @admin.display(description="Dominante titel (ingekort)")
    def dominant_title_short(self, obj):
        return obj.dominant_title[:80]

@admin.register(UniqueActivity)
class UniqueActivityAdmin(admin.ModelAdmin):
    list_display = ["block", "raw_title_short", "total_minutes"]
    list_filter = ["block__date", "block__app_name"]
    search_fields = ["raw_title", "block__app_name", "block__date", "block__started_at"]
    readonly_fields = ["block", "raw_title", "total_seconds",]
    # inlines = [WindowActivityInline] # werkt niet want many-to-many, ik denk dat dit fout is, dat het foreign key moet zijn, maar ik vraag claude als ik weer credits krijg

    @admin.display(description="Titel (ingekort)")
    def raw_title_short(self, obj):
        return obj.raw_title[:80]

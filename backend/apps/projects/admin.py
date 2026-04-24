from django.contrib import admin
from .models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["name", "color", "is_active", "created_at"]
    list_filter = ["is_active"]
    list_editable = ["is_active"]


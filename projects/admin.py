from django.contrib import admin

from .models import Project, Task, Tag, Comment


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "color")
    search_fields = ("name",)


class TaskInline(admin.TabularInline):
    model = Task
    extra = 0


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "owner", "category", "deadline", "created", "updated")
    list_filter = ("category", "deadline")
    search_fields = ("title", "description")
    autocomplete_fields = ("owner", "tags")
    inlines = [TaskInline]


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "project", "owner", "priority", "status", "due_date")
    list_filter = ("priority", "status")
    search_fields = ("title", "description")
    autocomplete_fields = ("owner", "project", "assignees", "depends_on", "tags")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "task", "owner", "created")
    search_fields = ("title", "description")
    autocomplete_fields = ("task", "owner")

from django.contrib import admin
from .models import Analysis


@admin.register(Analysis)
class AnalysisAdmin(admin.ModelAdmin):
    list_display = ("id", "jd_snippet", "match_score", "created_at")
    list_filter = ("created_at",)
    readonly_fields = ("created_at",)


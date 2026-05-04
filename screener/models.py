from django.db import models


class Analysis(models.Model):
    """Stores the result of a single resume-vs-JD analysis."""

    job_description = models.TextField(
        help_text="The full job description text."
    )
    resume_text = models.TextField(
        help_text="The extracted resume text (from textarea or PDF)."
    )
    resume_filename = models.CharField(
        max_length=255, blank=True, default="",
        help_text="Original PDF filename, if uploaded."
    )

    # ── Gemini results ──────────────────────────────────────
    match_score = models.IntegerField(
        default=0,
        help_text="Overall match percentage (0–100)."
    )
    matched_skills = models.JSONField(
        default=list, blank=True,
        help_text="List of skills found in both JD and resume."
    )
    missing_skills = models.JSONField(
        default=list, blank=True,
        help_text="Skills in JD but absent from resume."
    )
    summary = models.TextField(
        blank=True, default="",
        help_text="Short professional summary written by Gemini."
    )
    improvements = models.JSONField(
        default=list, blank=True,
        help_text="List of actionable improvement suggestions."
    )
    rewritten_bullets = models.JSONField(
        default=list, blank=True,
        help_text='List of {"before": ..., "after": ...} bullet rewrites.'
    )
    ats_keywords = models.JSONField(
        default=list, blank=True,
        help_text="Important ATS keywords to include."
    )

    # ── Meta ────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Analyses"

    def __str__(self):
        return f"Analysis #{self.pk} — {self.match_score}%"

    # ── Helpers for templates ───────────────────────────────
    @property
    def jd_snippet(self):
        """First 80 chars of the JD for admin list display."""
        return self.job_description[:80] + ("…" if len(self.job_description) > 80 else "")

    @property
    def score_color(self):
        """Bootstrap contextual color based on score."""
        if self.match_score >= 75:
            return "success"
        elif self.match_score >= 50:
            return "warning"
        return "danger"


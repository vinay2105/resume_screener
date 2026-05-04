"""
Views for the screener app.
"""

import logging
import pdfplumber
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from .models import Analysis
from .utils import analyze_resume

logger = logging.getLogger(__name__)

MAX_PDF_SIZE = 5 * 1024 * 1024  # 5 MB


def home(request):
    """Landing page with the analysis form."""

    if request.method == "POST":
        job_description = request.POST.get("job_description", "").strip()
        resume_text = request.POST.get("resume_text", "").strip()
        pdf_file = request.FILES.get("pdf_file")
        resume_filename = ""

        # ── Validate JD ───────────────────────────────────
        if not job_description:
            messages.error(request, "Please paste a job description.")
            return redirect("screener:home")

        # ── Handle PDF upload ─────────────────────────────
        if pdf_file:
            if pdf_file.size > MAX_PDF_SIZE:
                messages.error(request, "PDF too large. Maximum size is 5 MB.")
                return redirect("screener:home")

            if not pdf_file.name.lower().endswith(".pdf"):
                messages.error(request, "Only PDF files are accepted.")
                return redirect("screener:home")

            try:
                with pdfplumber.open(pdf_file) as pdf:
                    pages = [page.extract_text() or "" for page in pdf.pages]
                    extracted = "\n".join(pages).strip()
                if not extracted:
                    messages.error(
                        request,
                        "Could not extract text from this PDF. "
                        "Please paste your resume text instead.",
                    )
                    return redirect("screener:home")
                resume_text = extracted
                resume_filename = pdf_file.name
            except Exception as exc:
                logger.error("PDF extraction failed: %s", exc)
                messages.error(
                    request,
                    "Failed to read the PDF. Please paste your resume text instead.",
                )
                return redirect("screener:home")

        # ── Validate resume text ──────────────────────────
        if not resume_text:
            messages.error(request, "Please provide your resume text or upload a PDF.")
            return redirect("screener:home")

        # ── Call Gemini ───────────────────────────────────
        try:
            result = analyze_resume(job_description, resume_text)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect("screener:home")
        except RuntimeError as exc:
            messages.error(request, f"AI analysis failed: {exc}")
            return redirect("screener:home")
        except Exception as exc:
            logger.exception("Unexpected error during analysis")
            messages.error(
                request,
                "An unexpected error occurred. Please try again later.",
            )
            return redirect("screener:home")

        # ── Save to database ─────────────────────────────
        analysis = Analysis.objects.create(
            job_description=job_description,
            resume_text=resume_text,
            resume_filename=resume_filename,
            match_score=result["match_score"],
            matched_skills=result["matched_skills"],
            missing_skills=result["missing_skills"],
            summary=result["summary"],
            improvements=result["improvements"],
            rewritten_bullets=result["rewritten_bullets"],
            ats_keywords=result["ats_keywords"],
        )

        return redirect("screener:results", pk=analysis.pk)

    # GET — show form + recent analyses
    recent = Analysis.objects.all()[:5]
    return render(request, "screener/home.html", {"recent_analyses": recent})


def results(request, pk):
    """Display analysis results."""
    analysis = get_object_or_404(Analysis, pk=pk)
    return render(request, "screener/results.html", {"analysis": analysis})


def history(request):
    """Show all past analyses."""
    analyses = Analysis.objects.all()
    return render(request, "screener/history.html", {"analyses": analyses})
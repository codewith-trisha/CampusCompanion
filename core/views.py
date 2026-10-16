import json
import re

from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from .models import StudentProfile, Enrollment, Course, CollegeInformation, ChatLog, Assignment, TimetableSlot
from . import rag_engine


# ============================================================================
# LANDING & AUTH VIEWS
# ============================================================================

def landing_page(request):
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            return redirect('/secure-management-portal-xyz/')
        return redirect("dashboard")
    return render(request, "core/landing.html")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        auth_login(request, form.get_user())
        return redirect("dashboard")
    return render(request, "core/login.html", {"form": form})


def logout_view(request):
    auth_logout(request)
    return redirect("login")


# ============================================================================
# DASHBOARD — plain Django view/template, NO AI involved.
# This proves the data layer works on its own, independent of the chatbot.
# ============================================================================

@login_required
def dashboard(request):
    profile = StudentProfile.objects.select_related("user").get(user=request.user)
    enrollments = Enrollment.objects.filter(student=profile).select_related("course")

    completed = enrollments.filter(status="COMPLETED")
    ongoing = enrollments.filter(status="ONGOING")
    failed = enrollments.filter(status="FAILED")

    earned_credits = sum(e.course.credits for e in completed)
    remaining_credits = max(profile.required_credits_to_graduate - earned_credits, 0)

    # Fetch assignments and timetable slots for the logged-in user
    assignments = Assignment.objects.filter(student=request.user)
    timetable = TimetableSlot.objects.filter(student=request.user)

    context = {
        "profile": profile,
        "completed": completed,
        "ongoing": ongoing,
        "failed": failed,
        "earned_credits": earned_credits,
        "remaining_credits": remaining_credits,
        "assignments": assignments,
        "timetable": timetable,
    }
    return render(request, "core/dashboard.html", context)


# ============================================================================
# THE DUAL-ENGINE CHATBOT
# ============================================================================

PERSONAL_KEYWORDS = [
    "my", "i have", "i've", "credits", "credit", "marksheet", "mark sheet",
    "grade", "cgpa", "gpa", "backlog", "ongoing", "completed", "semester",
    "remaining", "yet to finish", "am i eligible", "can i graduate", "assignment", "timetable", "schedule"
]


def _looks_personal(message: str) -> bool:
    lowered = message.lower()
    return any(keyword in lowered for keyword in PERSONAL_KEYWORDS)


def _build_personal_context(user) -> str | None:
    try:
        profile = StudentProfile.objects.get(user=user)
    except StudentProfile.DoesNotExist:
        return None

    enrollments = Enrollment.objects.filter(student=profile).select_related("course")
    completed = enrollments.filter(status="COMPLETED")
    ongoing = enrollments.filter(status="ONGOING")
    failed = enrollments.filter(status="FAILED")

    earned_credits = sum(e.course.credits for e in completed)
    remaining_credits = max(profile.required_credits_to_graduate - earned_credits, 0)

    taken_course_ids = enrollments.values_list("course_id", flat=True)
    suggested_electives = Course.objects.filter(is_elective=True).exclude(id__in=taken_course_ids)[:5]

    assignments = Assignment.objects.filter(student=user)
    timetable = TimetableSlot.objects.filter(student=user)

    return f"""
[AUTHENTICATED STUDENT RECORD — for {profile.user.get_full_name() or profile.user.username} only]
Roll Number: {profile.roll_number}
Department: {profile.department}
Current Semester: {profile.current_semester}
Credits Earned: {earned_credits}
Credits Required to Graduate: {profile.required_credits_to_graduate}
Credits Remaining: {remaining_credits}
Completed Courses: {[f"{e.course.code} {e.course.title} (Grade: {e.grade or 'N/A'})" for e in completed] or "None yet"}
Ongoing Courses: {[f"{e.course.code} {e.course.title}" for e in ongoing] or "None"}
Backlogs / Failed Courses: {[f"{e.course.code} {e.course.title}" for e in failed] or "None"}
Assignments: {[f"{a.course_code}: {a.title} (Due: {a.due_date}, Submitted: {a.is_submitted})" for a in assignments] or "None"}
Timetable: {[f"{t.day} {t.start_time}-{t.end_time}: {t.course_name} at {t.room}" for t in timetable] or "None"}
Elective Suggestions to Fill Remaining Credits: {[f"{c.code} {c.title} ({c.credits} credits)" for c in suggested_electives] or "None available"}
""".strip()


_STOPWORDS = {
    "what", "when", "where", "which", "does", "the", "for", "and", "with",
    "about", "tell", "give", "can", "you", "how", "much", "are", "is", "of",
    "to", "in", "on", "me", "please", "would", "like", "know", "need",
}


def _build_rag_context(message: str) -> str | None:
    matches = rag_engine.search_documents(message, top_k=5)
    seen_titles = {m["title"] for m in matches}

    significant_words = [
        w for w in re.findall(r"[a-zA-Z]{4,}", message.lower()) if w not in _STOPWORDS
    ]
    if significant_words:
        keyword_filter = Q()
        for word in significant_words:
            keyword_filter |= Q(title__icontains=word) | Q(content__icontains=word)
        keyword_matches = CollegeInformation.objects.filter(keyword_filter)[:5]
        for doc in keyword_matches:
            if doc.title not in seen_titles:
                matches.append({"title": doc.title, "category": doc.category, "content": doc.content, "distance": None})
                seen_titles.add(doc.title)

    if not matches:
        return None

    chunks = [f"Document: {m['title']} ({m['category']})\n{m['content']}" for m in matches]
    return "\n\n".join(chunks)


SYSTEM_PROMPT_TEMPLATE = """You are the official digital CampusCompanion for the college.
Answer the student's question using the verified context provided below, and take the
conversation history into account for follow-up questions.
If the context does not contain the answer, say so honestly instead of guessing.
Keep answers short, friendly, and directly useful to a student.

{student_context}

{campus_context}

Rules:
- Only state personal academic facts (credits, grades, courses, assignments, timetable) that appear in the
  AUTHENTICATED STUDENT RECORD block above — never invent or assume numbers.
- For general campus questions (fees, timings, holidays, clubs), summarize the
  matched documents in your own words.
- If asked something outside both contexts, politely say you don't have that
  information yet and suggest they contact the relevant department.
"""

MAX_HISTORY_TURNS = 8
SESSION_KEY = "chat_history"


@login_required
@require_POST
def chat_api(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    message = (data.get("message") or "").strip()
    if not message:
        return JsonResponse({"error": "message field is required"}, status=400)

    history = request.session.get(SESSION_KEY, [])

    used_personal = _looks_personal(message)
    student_context = _build_personal_context(request.user) if used_personal else None
    campus_context = _build_rag_context(message)

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        student_context=student_context or "[No personal record needed for this question]",
        campus_context=f"[CAMPUS DOCUMENT CONTEXT]\n{campus_context}" if campus_context else "[No matching campus documents found]",
    )

    try:
        answer = rag_engine.ask_gemini(system_prompt, message, history=history)
    except RuntimeError as exc:
        return JsonResponse({"error": str(exc)}, status=500)

    history.append({"role": "user", "text": message})
    history.append({"role": "model", "text": answer})
    request.session[SESSION_KEY] = history[-(MAX_HISTORY_TURNS * 2):]

    ChatLog.objects.create(
        user=request.user,
        question=message,
        answer=answer,
        used_personal_data=bool(student_context),
        used_rag_documents=bool(campus_context),
    )

    return JsonResponse({"reply": answer})


@login_required
@require_POST
def chat_reset(request):
    request.session.pop(SESSION_KEY, None)
    return JsonResponse({"status": "ok"})
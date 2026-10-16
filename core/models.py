from django.db import models
from django.contrib.auth.models import User


# ============================================================================
# SIDE 1 — SECURE STUDENT DATA
# Everything here is only ever readable through Django's ORM, filtered by
# request.user. This is the "deterministic" engine — no AI, no guessing.
# ============================================================================

class StudentProfile(models.Model):
    """One row per student account. Linked 1-to-1 with Django's built-in User."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    roll_number = models.CharField(max_length=15, unique=True)
    department = models.CharField(max_length=80)
    current_semester = models.IntegerField(default=1)
    required_credits_to_graduate = models.IntegerField(default=160)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.roll_number})"


class Course(models.Model):
    """A course/subject offered by the college, with its credit value."""
    code = models.CharField(max_length=15, unique=True)
    title = models.CharField(max_length=150)
    credits = models.IntegerField()
    semester = models.IntegerField(help_text="Semester this course is normally taken in")
    is_elective = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.code} - {self.title} ({self.credits} credits)"


class Enrollment(models.Model):
    """Links a student to a course, with their status and grade."""
    STATUS_CHOICES = [
        ("COMPLETED", "Completed"),
        ("ONGOING", "Ongoing"),
        ("FAILED", "Failed / Backlog"),
    ]
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="ONGOING")
    grade = models.CharField(max_length=5, blank=True, null=True)   # e.g. "A", "B+"
    grade_point = models.FloatField(null=True, blank=True)          # e.g. 9.0 on a 10-point scale

    class Meta:
        unique_together = ("student", "course")

    def __str__(self):
        return f"{self.student.roll_number} - {self.course.code} ({self.status})"


# ============================================================================
# SIDE 1 EXTENSION — ASSIGNMENTS & TIMETABLE SLOTS
# ============================================================================

class Assignment(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=200)
    course_code = models.CharField(max_length=20)
    due_date = models.DateTimeField()
    is_submitted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.course_code} - {self.title}"


class TimetableSlot(models.Model):
    DAYS_OF_WEEK = [
        ('MON', 'Monday'),
        ('TUE', 'Tuesday'),
        ('WED', 'Wednesday'),
        ('THU', 'Thursday'),
        ('FRI', 'Friday'),
    ]
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='timetable_slots')
    day = models.CharField(max_length=3, choices=DAYS_OF_WEEK)
    course_name = models.CharField(max_length=100)
    start_time = models.TimeField()
    end_time = models.TimeField()
    room = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.day} ({self.start_time}-{self.end_time}): {self.course_name}"


# ============================================================================
# SIDE 2 — GENERAL CAMPUS INFORMATION (feeds the RAG / vector search engine)
# This is the loose, document-style knowledge: fees, timings, rules, holidays.
# Every row here gets embedded into a vector and stored in ChromaDB by the
# `build_vector_index` management command.
# ============================================================================

class CollegeInformation(models.Model):
    CATEGORY_CHOICES = [
        ("FEES", "Fees & Payments"),
        ("TIMINGS", "Timings & Schedules"),
        ("CLUBS", "Clubs, Sports & Extracurriculars"),
        ("EXAMS", "Exams, Hall Tickets & Results"),
        ("HOLIDAYS", "Academic Calendar & Holidays"),
        ("HOSTEL", "Hostel & Transport"),
        ("ACADEMIC_RULES", "Academic Rules & Policies"),
        ("SUPPORT", "Grievances & Support"),
        ("PLACEMENT", "Placements & Career"),
    ]
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    title = models.CharField(max_length=200)
    content = models.TextField(help_text="The actual answer/info text — this is what gets embedded.")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"[{self.category}] {self.title}"


class ChatLog(models.Model):
    """Optional but nice for a client demo: shows you log & can audit chatbot usage."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.TextField()
    answer = models.TextField()
    used_personal_data = models.BooleanField(default=False)
    used_rag_documents = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}: {self.question[:50]}"
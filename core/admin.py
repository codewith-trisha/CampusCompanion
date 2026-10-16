from django.contrib import admin
from .models import StudentProfile, Course, Enrollment, CollegeInformation, ChatLog, Assignment, TimetableSlot


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("roll_number", "user", "department", "current_semester", "required_credits_to_graduate")
    search_fields = ("roll_number", "user__username", "user__first_name", "user__last_name")


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "credits", "semester", "is_elective")
    list_filter = ("semester", "is_elective")
    search_fields = ("code", "title")


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "status", "grade", "grade_point")
    list_filter = ("status",)
    search_fields = ("student__roll_number", "course__code")


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ("title", "student", "course_code", "due_date", "is_submitted")
    list_filter = ("is_submitted", "due_date")
    search_fields = ("title", "course_code", "student__username")


@admin.register(TimetableSlot)
class TimetableSlotAdmin(admin.ModelAdmin):
    list_display = ("course_name", "student", "day", "start_time", "end_time", "room")
    list_filter = ("day",)
    search_fields = ("course_name", "room", "student__username")


@admin.register(CollegeInformation)
class CollegeInformationAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "updated_at")
    list_filter = ("category",)
    search_fields = ("title", "content")


@admin.register(ChatLog)
class ChatLogAdmin(admin.ModelAdmin):
    list_display = ("user", "question", "used_personal_data", "used_rag_documents", "created_at")
    list_filter = ("used_personal_data", "used_rag_documents")
    readonly_fields = ("user", "question", "answer", "used_personal_data", "used_rag_documents", "created_at")
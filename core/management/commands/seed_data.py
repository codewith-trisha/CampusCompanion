from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from core.models import StudentProfile, Course, Enrollment, CollegeInformation


class Command(BaseCommand):
    help = "Populates the database with realistic demo data covering every student use case."

    def handle(self, *args, **options):
        self.stdout.write("Seeding courses...")
        courses = self._seed_courses()

        self.stdout.write("Seeding students + enrollments...")
        self._seed_students(courses)

        self.stdout.write("Seeding campus information (RAG documents)...")
        self._seed_campus_information()

        self.stdout.write(self.style.SUCCESS(
            "\nDone! Demo logins (username / password):\n"
            "  rahul / campus1234   (final-year student, near graduation)\n"
            "  priya / campus1234   (mid-course student with a backlog)\n"
            "  arjun / campus1234   (first-semester student)\n\n"
            "Next step: run `python manage.py build_vector_index` to embed the campus documents."
        ))

    # ------------------------------------------------------------------
    def _seed_courses(self):
        course_data = [
            # code, title, credits, semester, is_elective
            ("CS101", "Programming Fundamentals", 4, 1, False),
            ("MA101", "Engineering Mathematics I", 4, 1, False),
            ("PH101", "Engineering Physics", 3, 1, False),
            ("CS102", "Data Structures", 4, 2, False),
            ("MA102", "Engineering Mathematics II", 4, 2, False),
            ("CS201", "Object Oriented Programming", 4, 2, False),
            ("CS202", "Database Management Systems", 4, 3, False),
            ("CS203", "Operating Systems", 4, 3, False),
            ("CS204", "Computer Networks", 3, 3, False),
            ("CS301", "Machine Learning", 4, 4, False),
            ("CS302", "Web Technologies", 3, 4, False),
            ("CS303", "Software Engineering", 3, 4, False),
            ("CS401", "Cloud Computing", 3, 5, False),
            ("CS402", "Natural Language Processing", 3, 5, False),
            ("CS403", "Artificial Intelligence", 4, 5, False),
            ("CSE501", "Deep Learning (Elective)", 3, 6, True),
            ("CSE502", "Blockchain Technology (Elective)", 3, 6, True),
            ("CSE503", "Cybersecurity Fundamentals (Elective)", 3, 6, True),
            ("CSE504", "Data Visualization (Elective)", 3, 6, True),
            ("HS101", "Professional Communication", 2, 1, False),
        ]
        courses = {}
        for code, title, credits, semester, is_elective in course_data:
            course, _ = Course.objects.get_or_create(
                code=code,
                defaults={"title": title, "credits": credits, "semester": semester, "is_elective": is_elective},
            )
            courses[code] = course
        return courses

    # ------------------------------------------------------------------
    def _seed_students(self, courses):
        # --- Student 1: Rahul — final semester, close to graduation, no backlogs ---
        rahul_user, _ = User.objects.get_or_create(
            username="rahul", defaults={"first_name": "Rahul", "last_name": "Sharma", "email": "rahul@example.com"}
        )
        rahul_user.set_password("campus1234")
        rahul_user.save()
        rahul_profile, _ = StudentProfile.objects.get_or_create(
            user=rahul_user,
            defaults={"roll_number": "21CSE001", "department": "Computer Science & Engineering",
                      "current_semester": 6, "required_credits_to_graduate": 160},
        )
        rahul_completed = ["CS101", "MA101", "PH101", "CS102", "MA102", "CS201", "CS202",
                            "CS203", "CS204", "CS301", "CS302", "CS303", "HS101"]
        rahul_ongoing = ["CS401", "CS402", "CS403"]
        self._enroll(rahul_profile, courses, rahul_completed, "COMPLETED")
        self._enroll(rahul_profile, courses, rahul_ongoing, "ONGOING")

        # --- Student 2: Priya — mid-course, one backlog ---
        priya_user, _ = User.objects.get_or_create(
            username="priya", defaults={"first_name": "Priya", "last_name": "Reddy", "email": "priya@example.com"}
        )
        priya_user.set_password("campus1234")
        priya_user.save()
        priya_profile, _ = StudentProfile.objects.get_or_create(
            user=priya_user,
            defaults={"roll_number": "22CSE045", "department": "Computer Science & Engineering",
                      "current_semester": 4, "required_credits_to_graduate": 160},
        )
        priya_completed = ["CS101", "MA101", "PH101", "CS102", "MA102", "HS101"]
        priya_ongoing = ["CS202", "CS204", "CS301"]
        priya_failed = ["CS201"]  # backlog
        self._enroll(priya_profile, courses, priya_completed, "COMPLETED")
        self._enroll(priya_profile, courses, priya_ongoing, "ONGOING")
        self._enroll(priya_profile, courses, priya_failed, "FAILED")

        # --- Student 3: Arjun — first semester, just started ---
        arjun_user, _ = User.objects.get_or_create(
            username="arjun", defaults={"first_name": "Arjun", "last_name": "Verma", "email": "arjun@example.com"}
        )
        arjun_user.set_password("campus1234")
        arjun_user.save()
        arjun_profile, _ = StudentProfile.objects.get_or_create(
            user=arjun_user,
            defaults={"roll_number": "24CSE112", "department": "Computer Science & Engineering",
                      "current_semester": 1, "required_credits_to_graduate": 160},
        )
        arjun_ongoing = ["CS101", "MA101", "PH101", "HS101"]
        self._enroll(arjun_profile, courses, arjun_ongoing, "ONGOING")

        # Add grades to completed courses for realism
        grade_map = {"COMPLETED": [("A", 9.0), ("B+", 8.0), ("A+", 10.0), ("B", 7.0)]}
        import itertools
        cycle = itertools.cycle(grade_map["COMPLETED"])
        for e in Enrollment.objects.filter(status="COMPLETED", grade__isnull=True):
            grade, gp = next(cycle)
            e.grade, e.grade_point = grade, gp
            e.save()

    def _enroll(self, student_profile, courses, course_codes, status):
        for code in course_codes:
            Enrollment.objects.get_or_create(
                student=student_profile, course=courses[code], defaults={"status": status}
            )

    # ------------------------------------------------------------------
    def _seed_campus_information(self):
        entries = [
            # ---- FEES ----
            ("FEES", "Sports Club Membership Fee",
             "Joining the Sports Club costs ₹500 per academic year. This covers access to the gym, "
             "cricket ground, badminton courts, and table tennis room. Payment can be made online via "
             "the student portal under 'Club Fees' or at the accounts office."),
            ("FEES", "Cultural Club Membership Fee",
             "The fee for cultural programs and the Cultural Club (music, dance, drama) is ₹300 per "
             "year, payable at the Student Activity Center or online through the fee portal."),
            ("FEES", "Hostel Fee Structure",
             "Hostel fee is ₹85,000 per year for a triple-sharing room and ₹1,10,000 per year for a "
             "double-sharing room, inclusive of mess charges. Fees are payable in two installments: "
             "before semester 1 and before semester 2."),
            ("FEES", "Exam Re-evaluation Fee",
             "Requesting re-evaluation of an exam paper costs ₹300 per subject. Applications must be "
             "submitted within 7 days of result declaration through the examination cell."),
            ("FEES", "Transport/Bus Fee",
             "College bus transport fee ranges from ₹12,000 to ₹22,000 per year depending on the route "
             "distance from campus. Routes and stops are listed on the transport office notice board."),

            # ---- TIMINGS ----
            ("TIMINGS", "Library Timings",
             "The central library is open Monday to Saturday from 8:00 AM to 8:00 PM, and Sunday from "
             "10:00 AM to 4:00 PM. It remains closed on national holidays."),
            ("TIMINGS", "Canteen Timings",
             "The main canteen serves breakfast from 7:30–9:30 AM, lunch from 12:30–2:30 PM, and snacks/"
             "dinner from 4:30–8:00 PM on all working days."),
            ("TIMINGS", "Administrative Office Timings",
             "The administrative office (fees, certificates, bonafide letters) is open Monday to Friday, "
             "9:30 AM to 5:00 PM, and Saturday 9:30 AM to 1:00 PM."),
            ("TIMINGS", "College Bus Timings",
             "Morning pickup buses depart from all routes between 7:00 AM and 7:45 AM. Return buses "
             "depart from campus at 4:30 PM and 5:30 PM on regular working days."),

            # ---- CLUBS ----
            ("CLUBS", "NCC (National Cadet Corps) Credits",
             "Joining NCC earns students 2 extra credits per year, recognized as a co-curricular credit "
             "toward the total graduation requirement. Enrollment happens at the start of semester 1 or 3."),
            ("CLUBS", "NSS (National Service Scheme) Credits",
             "Active NSS participation (minimum 120 hours of social service per year) earns 2 credits, "
             "counted as co-curricular credit. Registration is open at the start of every academic year."),
            ("CLUBS", "Coding Club Benefits",
             "The Coding Club does not carry academic credits but provides certificates of participation "
             "for hackathons, which are valued during placement interviews. Membership is free."),
            ("CLUBS", "Joining Sports Teams",
             "Students trying out for inter-college sports teams (cricket, basketball, athletics) can "
             "earn 1 credit per year for regular participation, in addition to the ₹500 sports club fee."),

            # ---- EXAMS ----
            ("EXAMS", "Hall Ticket Download Process",
             "Hall tickets are released 10 days before exams on the student portal under 'Examinations > "
             "Hall Ticket'. Students with unpaid fees or attendance shortage will not see a download option "
             "and must clear dues at the accounts office first."),
            ("EXAMS", "Exam Timetable Release",
             "The semester exam timetable is published 3 weeks before exams on the college website and "
             "notice boards, and is also sent via the registered student email."),
            ("EXAMS", "Backlog / Reappear Exam Rules",
             "Students with a backlog (failed course) can reappear in the next semester's supplementary "
             "exam window. A maximum of 3 backlogs can be carried at any time; more than that requires "
             "special department permission to continue to the next semester."),
            ("EXAMS", "Minimum Attendance for Exam Eligibility",
             "Students must maintain at least 75% attendance per subject to be eligible to sit for the "
             "semester exam. Attendance between 65-75% requires a condonation fee and HOD approval."),

            # ---- HOLIDAYS / ACADEMIC CALENDAR ----
            ("HOLIDAYS", "Semester Break Schedule",
             "Winter break runs for 2 weeks in late December, and summer break runs for 6 weeks from "
             "mid-May to end of June. Exact dates are published in the yearly academic calendar."),
            ("HOLIDAYS", "Festival & National Holidays",
             "The college observes all national holidays (Republic Day, Independence Day, Gandhi Jayanti) "
             "plus major regional festivals like Diwali, Sankranti, and Ugadi, as listed in the academic "
             "calendar released each July."),

            # ---- HOSTEL / TRANSPORT ----
            ("HOSTEL", "Hostel Curfew and Rules",
             "Hostel gates close at 9:30 PM on weekdays and 10:30 PM on weekends. Late entries require "
             "warden approval and are logged. Overnight outings require prior written permission from parents."),

            # ---- ACADEMIC RULES ----
            ("ACADEMIC_RULES", "Credit System Explained",
             "Each course carries a fixed number of credits based on its weekly teaching hours. A B.Tech "
             "degree requires 160 total credits across 8 semesters, including core courses, electives, "
             "and co-curricular activities like NCC/NSS/sports."),
            ("ACADEMIC_RULES", "Minimum CGPA Requirements",
             "Students must maintain a minimum CGPA of 5.0 to remain in good academic standing. A CGPA "
             "below 5.0 for two consecutive semesters triggers mandatory academic counseling."),

            # ---- SUPPORT ----
            ("SUPPORT", "Grievance Cell Contact",
             "Academic or personal grievances can be raised confidentially through the Grievance Cell "
             "portal or by emailing grievance@college.edu. Responses are typically provided within 5 "
             "working days."),
            ("SUPPORT", "Counseling Services",
             "Free confidential counseling sessions are available Monday to Friday, 10 AM to 4 PM, at "
             "the Student Wellness Center. Appointments can be booked through the student portal."),

            # ---- PLACEMENT ----
            ("PLACEMENT", "Placement Eligibility Criteria",
             "Students need a minimum CGPA of 6.0 and no active backlogs to be eligible for on-campus "
             "placements. Registration for the placement cell opens at the start of the 6th semester."),
        ]

        for category, title, content in entries:
            CollegeInformation.objects.get_or_create(
                title=title, defaults={"category": category, "content": content}
            )

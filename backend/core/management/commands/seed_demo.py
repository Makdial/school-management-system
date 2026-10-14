"""Idempotent demo data seeder.

Running this command twice never duplicates rows: every record is created with
``get_or_create`` keyed on its natural key. Use ``--fresh`` to wipe the demo
school (and everything cascading from it) before reseeding.

    python manage.py seed_demo
    python manage.py seed_demo --students 40 --fresh

The demo password is taken from ``DEMO_PASSWORD`` (default ``Demo@12345``).
"""
import os
import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from academics.models import ClassSubject, StudentEnrollment, Subject
from admissions.models import AdmissionApplication
from assignments.models import Assignment, Submission
from attendance.services import bulk_upsert_attendance
from communications.models import Announcement, Notification
from examinations.models import Exam, ExamSubject, ReportCard, StudentMark
from examinations.services import compute_report_cards, enter_marks, publish_results
from finance.models import (
    FeeCategory, FeeStructure, FeeStructureItem, Invoice,
)
from finance.services import create_invoice, record_payment
from hr.models import Contract, LeaveRequest, LeaveType, StaffProfile
from library.models import Book, BookCategory, BookCopy, Borrowing
from library.services import borrow_book
from schools.models import (
    AcademicSession, Department, GradeLevel, GradingBand, GradingScale, Holiday,
    School, SchoolEvent, SchoolSetting, Section, Term,
)
from students.models import Guardian, Student, StudentGuardian
from timetable.models import Room, TimetableEntry, TimetablePeriod
from transport.models import (
    StudentTransportAssignment, TransportRoute, TransportStop, Vehicle,
)

User = get_user_model()

GRADES = [("G7", "Grade 7", 1), ("G8", "Grade 8", 2), ("G9", "Grade 9", 3)]
SUBJECTS = [
    ("MAT", "Mathematics"),
    ("ENG", "English Language"),
    ("SCI", "Integrated Science"),
    ("HIS", "History"),
]
FIRST_NAMES = [
    "Amina", "Ben", "Chloe", "Daniel", "Ella", "Farid", "Grace", "Hassan",
    "Ivy", "Jonas", "Kira", "Liam", "Maya", "Noah", "Omar", "Priya",
    "Quinn", "Rosa", "Sam", "Tara", "Uma", "Victor", "Wendy", "Xavier",
]
LAST_NAMES = [
    "Adams", "Baker", "Chen", "Diallo", "Evans", "Fischer", "Garcia", "Hassan",
    "Ibrahim", "Jones", "Khan", "Lopez", "Mensah", "Nguyen", "Owusu", "Patel",
]

ROLE_USERS = [
    ("schooladmin", "SCHOOL_ADMIN", "Ada", "Admin", "School administrator"),
    ("principal", "PRINCIPAL", "Paul", "Principal", "Principal / headteacher"),
    ("teacher", "TEACHER", "Tina", "Teacher", "Class teacher"),
    ("accountant", "ACCOUNTANT", "Alex", "Accountant", "Fees & finance"),
    ("librarian", "LIBRARIAN", "Lucy", "Librarian", "Library desk"),
    ("transport", "TRANSPORT_MANAGER", "Tom", "Transport", "Transport manager"),
    ("hr", "HR_MANAGER", "Helen", "HR", "HR manager"),
    ("parent", "PARENT", "Pam", "Parent", "Parent / guardian"),
]


class Command(BaseCommand):
    help = "Seed idempotent demo data for a demo school."

    def add_arguments(self, parser):
        parser.add_argument("--students", type=int, default=24)
        parser.add_argument("--fresh", action="store_true", help="Delete the demo school first.")
        parser.add_argument("--password", default=os.getenv("DEMO_PASSWORD", "Demo@12345"))

    def handle(self, *args, **options):
        random.seed(42)
        self.password = options["password"]
        self.students_count = max(options["students"], 6)
        self.credentials = []

        if options["fresh"]:
            call_command("flush", interactive=False, verbosity=0)
            self.stdout.write(self.style.WARNING("Flushed the database before seeding."))

        with transaction.atomic():
            school = self._school()
            session, term = self._calendar(school)
            grades, sections = self._structure(school)
            subjects, class_subjects = self._academics(school, session, grades)
            self._grading(school)
            users = self._users(school)
            students = self._students(school, session, grades, sections, users)
            self._staff(school, users)
            self._attendance(school, session, sections, students, users)
            self._admissions(school, session, grades)
            self._finance(school, session, term, grades, students, users)
            self._examinations(school, session, term, class_subjects, students, users)
            self._timetable(school, session, sections, subjects, users)
            self._assignments(school, class_subjects, students, users)
            self._library(school, students, users)
            self._transport(school, students, users)
            self._communications(school, students, users)
            self._settings(school)

        self.stdout.write(self.style.SUCCESS(f"Demo data ready for '{school.name}'."))
        self.stdout.write(f"All accounts use password: {self.password}")
        for username, role, label in self.credentials:
            self.stdout.write(f"  {username:<12} {role:<18} {label}")

    # ------------------------------------------------------------------ blocks
    def _school(self):
        school, _ = School.objects.update_or_create(
            code="GWA",
            defaults={
                "name": "Greenwood Academy",
                "email": "info@greenwood.demo",
                "phone": "+1000000000",
                "address": "12 Learning Way, Springfield",
                "motto": "Knowledge, Integrity, Service",
                "website": "https://greenwood.demo",
                "currency": "USD",
                "is_active": True,
            },
        )
        return school

    def _calendar(self, school):
        today = timezone.localdate()
        start = today.replace(month=9, day=1)
        if start > today:
            start = start.replace(year=today.year - 1)
        session, _ = AcademicSession.objects.update_or_create(
            school=school,
            name=f"{start.year}/{start.year + 1}",
            defaults={"start_date": start, "end_date": start + timedelta(days=300)},
        )
        session.is_current = True
        session.save(update_fields=["is_current"])
        term, _ = Term.objects.update_or_create(
            session=session,
            name="FIRST",
            defaults={"start_date": session.start_date, "end_date": session.start_date + timedelta(days=105)},
        )
        term.is_current = True
        term.save(update_fields=["is_current"])
        return session, term

    def _structure(self, school):
        grades, sections = {}, {}
        for code, name, order in GRADES:
            grade, _ = GradeLevel.objects.get_or_create(
                school=school, code=code, defaults={"name": name, "level_order": order}
            )
            grades[code] = grade
            for stream in ("A", "B"):
                section, _ = Section.objects.get_or_create(
                    school=school, grade_level=grade, name=stream, defaults={"capacity": 40}
                )
                sections[(code, stream)] = section
                for suffix in ("1", "2"):
                    Room.objects.get_or_create(
                        school=school, name=f"{name}-{stream}{suffix}", defaults={"capacity": 40}
                    )
        for name, code in (("Science", "SCI"), ("Humanities", "HUM"), ("Administration", "ADM")):
            Department.objects.get_or_create(school=school, code=code, defaults={"name": name})
        return grades, sections

    def _academics(self, school, session, grades):
        subjects = {}
        for code, name in SUBJECTS:
            subject, _ = Subject.objects.get_or_create(
                school=school, code=code, defaults={"name": name}
            )
            subjects[code] = subject
        class_subjects = {}
        for gcode, grade in grades.items():
            for code in ("MAT", "ENG", "SCI"):
                cs, _ = ClassSubject.objects.get_or_create(
                    school=school, session=session, grade_level=grade, subject=subjects[code],
                    defaults={"periods_per_week": 5, "is_compulsory": True},
                )
                class_subjects[(gcode, code)] = cs
        return subjects, class_subjects

    def _grading(self, school):
        scale, _ = GradingScale.objects.get_or_create(
            school=school, name="Default Scale", defaults={"is_default": True}
        )
        scale.is_default = True
        scale.save(update_fields=["is_default"])
        for grade, lo, hi, remark in [
            ("A", 80, 100, "Excellent"), ("B", 70, 79.99, "Very Good"),
            ("C", 60, 69.99, "Good"), ("D", 50, 59.99, "Pass"), ("F", 0, 49.99, "Fail"),
        ]:
            GradingBand.objects.get_or_create(
                scale=scale, grade=grade,
                defaults={"min_score": Decimal(str(lo)), "max_score": Decimal(str(hi)), "remark": remark},
            )

    def _user(self, username, role, first, last, school):
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "user_type": role,
                "school": school,
                "first_name": first,
                "last_name": last,
                "email": f"{username}@greenwood.demo",
                "is_staff": role in ("SUPERADMIN", "SCHOOL_ADMIN"),
            },
        )
        if created:
            user.set_password(self.password)
            user.save()
        else:
            changed = False
            if user.user_type != role:
                user.user_type = role
                changed = True
            if user.school_id != (school.id if school else None):
                user.school = school
                changed = True
            if changed:
                user.save(update_fields=["user_type", "school"])
        return user

    def _users(self, school):
        self._user("superadmin", "SUPERADMIN", "Super", "Admin", None)
        users = {"superadmin": User.objects.get(username="superadmin")}
        for username, role, first, last, label in ROLE_USERS:
            key = role.lower()
            users[key] = self._user(username, role, first, last, school)
            self.credentials.append((username, role, label))
        return users

    def _students(self, school, session, grades, sections, users):
        students = []
        for index in range(1, self.students_count + 1):
            first = FIRST_NAMES[index % len(FIRST_NAMES)]
            last = LAST_NAMES[index % len(LAST_NAMES)]
            user = self._user(f"student{index}", "STUDENT", first, last, school)
            if index <= 3:
                self.credentials.append((f"student{index}", "STUDENT", f"Student #{index} ({first} {last})"))
            student, _ = Student.objects.get_or_create(
                school=school,
                admission_number=f"GWA-2026-{index:03d}",
                defaults={
                    "user": user,
                    "first_name": first,
                    "last_name": last,
                    "gender": "M" if index % 2 else "F",
                    "status": "ACTIVE",
                    "admission_date": session.start_date,
                },
            )
            gcode = GRADES[(index - 1) % len(GRADES)][0]
            stream = "A" if index % 2 else "B"
            StudentEnrollment.objects.get_or_create(
                student=student, session=session,
                defaults={
                    "school": school,
                    "grade_level": grades[gcode],
                    "section": sections[(gcode, stream)],
                    "status": "ACTIVE",
                    "roll_number": f"{index:02d}",
                },
            )
            students.append(student)

        guardians = {}
        for student in students:
            guardian = guardians.get(student.last_name)
            if guardian is None:
                guardian, _ = Guardian.objects.get_or_create(
                    school=school, first_name="Guardian", last_name=student.last_name
                )
                guardians[student.last_name] = guardian
                if guardian.user_id is None and users.get("parent"):
                    guardian.user = users["parent"]
                    guardian.save(update_fields=["user"])
            StudentGuardian.objects.get_or_create(
                student=student, guardian=guardian,
                defaults={"is_primary": True},
            )
        return students

    def _staff(self, school, users):
        today = timezone.localdate()
        profiles = [
            ("teacher", "EMP-001", "Mathematics Teacher", "Science"),
            ("principal", "EMP-002", "Principal", "Administration"),
            ("accountant", "EMP-003", "Accountant", "Administration"),
            ("librarian", "EMP-004", "Librarian", "Administration"),
            ("transport_manager", "EMP-005", "Transport Manager", "Administration"),
            ("hr_manager", "EMP-006", "HR Manager", "Administration"),
        ]
        staff = {}
        for key, emp_id, title, dept_name in profiles:
            user = users.get(key)
            if not user:
                continue
            dept = Department.objects.filter(school=school, name=dept_name).first()
            profile, _ = StaffProfile.objects.get_or_create(
                school=school, employee_id=emp_id,
                defaults={
                    "user": user,
                    "job_title": title,
                    "department": dept,
                    "employment_type": "FULL_TIME",
                    "hire_date": today - timedelta(days=400),
                    "salary": Decimal("2500.00"),
                    "status": "ACTIVE",
                },
            )
            staff[key] = profile
            Contract.objects.get_or_create(
                staff=profile, start_date=profile.hire_date,
                defaults={"salary": profile.salary or Decimal("0.00")},
            )
        for name, days in (("Annual Leave", 20), ("Sick Leave", 10), ("Maternity Leave", 90)):
            LeaveType.objects.get_or_create(
                school=school, name=name, defaults={"max_days_per_year": days}
            )
        teacher = staff.get("teacher")
        leave_type = LeaveType.objects.filter(school=school, name="Annual Leave").first()
        if teacher and leave_type:
            LeaveRequest.objects.get_or_create(
                school=school, staff=teacher, leave_type=leave_type,
                start_date=today + timedelta(days=10),
                defaults={"end_date": today + timedelta(days=12), "status": "PENDING"},
            )
        return staff

    def _attendance(self, school, session, sections, students, users):
        recorder = users.get("teacher") or users.get("school_admin")
        roll = ["PRESENT"] * 8 + ["LATE", "ABSENT", "EXCUSED"]
        today = timezone.localdate()
        for offset in range(1, 8):
            day = today - timedelta(days=offset)
            if day.weekday() >= 5:
                continue
            for section in sections.values():
                section_students = list(
                    Student.objects.filter(
                        school=school, enrollments__session=session, enrollments__section=section
                    ).distinct()
                )
                if not section_students:
                    continue
                records = [{"student": str(s.id), "status": random.choice(roll)} for s in section_students]
                bulk_upsert_attendance(school, session, day, section, records, recorder)

    def _admissions(self, school, session, grades):
        for index, status in enumerate(
            ["SUBMITTED", "UNDER_REVIEW", "APPROVED", "REJECTED", "ENROLLED"], start=1
        ):
            AdmissionApplication.objects.get_or_create(
                school=school, application_number=f"APP-2026-{index:04d}",
                defaults={
                    "session": session,
                    "grade_level": grades[GRADES[index % len(GRADES)][0]],
                    "applicant_first_name": FIRST_NAMES[index],
                    "applicant_last_name": LAST_NAMES[index],
                    "gender": "M" if index % 2 else "F",
                    "guardian_name": f"Parent {LAST_NAMES[index]}",
                    "guardian_phone": "+1000000000",
                    "status": status,
                },
            )

    def _finance(self, school, session, term, grades, students, users):
        categories = {}
        for code, name in (("TUITION", "Tuition"), ("TRANSPORT", "Transport"), ("LIBRARY", "Library")):
            categories[code], _ = FeeCategory.objects.get_or_create(
                school=school, code=code, defaults={"name": name}
            )
        for gcode, grade in grades.items():
            structure, _ = FeeStructure.objects.get_or_create(
                school=school, session=session, grade_level=grade, name="Standard Fees",
                defaults={"is_active": True},
            )
            for code, amount in (("TUITION", "600.00"), ("LIBRARY", "25.00")):
                FeeStructureItem.objects.get_or_create(
                    fee_structure=structure, category=categories[code],
                    defaults={"amount": Decimal(amount)},
                )

        accountant = users.get("accountant") or users.get("school_admin")
        created = 0
        for index, student in enumerate(students, start=1):
            if Invoice.objects.filter(school=school, student=student, session=session).exists():
                continue
            invoice = create_invoice(
                school=school, student=student, session=session, term=term,
                due_date=session.start_date + timedelta(days=30),
                items=[
                    {"category": categories["TUITION"], "description": "Tuition", "amount": Decimal("600.00")},
                    {"category": categories["LIBRARY"], "description": "Library", "amount": Decimal("25.00")},
                ],
            )
            created += 1
            if index % 3 != 0:
                fraction = Decimal("0.50") if index % 4 != 0 else Decimal("1.00")
                amount = (invoice.balance * fraction).quantize(Decimal("0.01"))
                if amount > 0:
                    record_payment(
                        invoice, amount, "CASH", accountant,
                        reference=f"RCPT-{index:04d}", paid_at=timezone.now(),
                    )
        if created:
            self.stdout.write(f"  created {created} invoices")

    def _examinations(self, school, session, term, class_subjects, students, users):
        teacher = users.get("teacher") or users.get("school_admin")
        exam, _ = Exam.objects.get_or_create(
            school=school, session=session, name="End of Term Examination",
            defaults={
                "term": term,
                "exam_type": "ENDTERM",
                "start_date": session.start_date + timedelta(days=80),
                "end_date": session.start_date + timedelta(days=90),
            },
        )
        exam_subjects = []
        for cs in class_subjects.values():
            es, _ = ExamSubject.objects.get_or_create(
                exam=exam, class_subject=cs,
                defaults={
                    "school": school,
                    "exam_date": exam.start_date,
                    "max_marks": Decimal("100"),
                    "pass_marks": Decimal("40"),
                },
            )
            exam_subjects.append(es)

        for es in exam_subjects:
            if exam.is_published:
                break
            if StudentMark.objects.filter(exam_subject=es).exists():
                continue
            grade_students = Student.objects.filter(
                school=school,
                enrollments__session=session,
                enrollments__grade_level=es.class_subject.grade_level,
            ).distinct()
            records = [
                {"student": str(s.id), "marks_obtained": Decimal(str(random.randint(35, 98)))}
                for s in grade_students
            ]
            if records:
                enter_marks(es, records, teacher)

        if exam_subjects and not ReportCard.objects.filter(exam=exam).exists():
            compute_report_cards(exam, teacher)
        if exam_subjects and not exam.is_published:
            publish_results(exam)

    def _timetable(self, school, session, sections, subjects, users):
        teacher = users.get("teacher") or users.get("school_admin")
        periods = []
        for order, (name, start, end) in enumerate(
            [("P1", "08:00", "08:45"), ("P2", "08:45", "09:30"), ("P3", "09:30", "10:15"),
             ("P4", "10:45", "11:30"), ("P5", "11:30", "12:15")],
            start=1,
        ):
            period, _ = TimetablePeriod.objects.get_or_create(
                school=school, name=name,
                defaults={"start_time": start, "end_time": end, "order": order},
            )
            periods.append(period)
        subject_cycle = list(subjects.values())
        for section in sections.values():
            for day in range(5):
                for index, period in enumerate(periods):
                    TimetableEntry.objects.get_or_create(
                        school=school, session=session, section=section,
                        day_of_week=day, period=period,
                        defaults={
                            "subject": subject_cycle[(day + index) % len(subject_cycle)],
                            "teacher": teacher,
                        },
                    )

    def _assignments(self, school, class_subjects, students, users):
        teacher = users.get("teacher") or users.get("school_admin")
        for cs in list(class_subjects.values())[:3]:
            assignment, _ = Assignment.objects.get_or_create(
                school=school, class_subject=cs, title=f"{cs.subject.name} Worksheet",
                defaults={
                    "description": "Complete the worksheet and submit online.",
                    "due_date": timezone.now() + timedelta(days=7),
                    "created_by": teacher,
                },
            )
            grade_students = list(
                Student.objects.filter(
                    school=school, enrollments__grade_level=cs.grade_level
                ).distinct()[:5]
            )
            for student in grade_students:
                Submission.objects.get_or_create(
                    assignment=assignment, student=student,
                    defaults={
                        "content": "Submitted online.",
                        "score": Decimal(str(random.randint(50, 100))),
                        "graded_by": teacher,
                        "graded_at": timezone.now(),
                    },
                )

    def _library(self, school, students, users):
        librarian = users.get("librarian") or users.get("school_admin")
        category, _ = BookCategory.objects.get_or_create(
            school=school, name="General", defaults={"code": "GEN"}
        )
        titles = [
            ("Things Fall Apart", "Chinua Achebe"),
            ("A Brief History of Time", "Stephen Hawking"),
            ("Mathematics for Secondary Schools", "Various"),
            ("The River Between", "Ngugi wa Thiong'o"),
        ]
        copies = []
        for index, (title, author) in enumerate(titles, start=1):
            book, _ = Book.objects.get_or_create(
                school=school, title=title,
                defaults={
                    "author": author, "category": category,
                    "isbn": f"978-0-00-{index:05d}",
                    "total_copies": 3, "available_copies": 3,
                },
            )
            for n in range(1, 4):
                copy, _ = BookCopy.objects.get_or_create(
                    book=book, copy_code=f"C{n}", defaults={"status": "AVAILABLE"}
                )
                copies.append(copy)
        if not Borrowing.objects.filter(school=school).exists() and len(copies) >= 3:
            borrowers = [s.user for s in students[:3] if s.user]
            for copy, borrower in zip(copies, borrowers):
                try:
                    borrow_book(school, borrower, copy, issued_by=librarian)
                except ValueError:
                    pass

    def _transport(self, school, students, users):
        vehicle, _ = Vehicle.objects.get_or_create(
            school=school, plate_number="KDA-123X",
            defaults={
                "make": "Toyota", "model": "Coaster", "capacity": 45,
                "driver_name": "John Driver", "status": "ACTIVE",
            },
        )
        route, _ = TransportRoute.objects.get_or_create(
            school=school, name="Downtown Route", defaults={"vehicle": vehicle}
        )
        stop, _ = TransportStop.objects.get_or_create(
            route=route, name="Central Station",
            defaults={"sequence": 1, "monthly_fee": Decimal("40.00")},
        )
        TransportStop.objects.get_or_create(
            route=route, name="Market Square",
            defaults={"sequence": 2, "monthly_fee": Decimal("35.00")},
        )
        for student in students[:4]:
            StudentTransportAssignment.objects.get_or_create(
                student=student, route=route,
                defaults={
                    "school": school, "stop": stop, "is_active": True,
                    "start_date": timezone.localdate(),
                },
            )

    def _communications(self, school, students, users):
        Announcement.objects.get_or_create(
            school=school, title="Welcome to the New Term",
            defaults={
                "body": "We are glad to have everyone back for the new term.",
                "audience": "ALL", "author": users.get("school_admin"),
                "is_published": True, "published_at": timezone.now(),
            },
        )
        SchoolEvent.objects.get_or_create(
            school=school, title="Parent-Teacher Meeting",
            defaults={
                "event_type": "MEETING", "audience": "PARENTS",
                "start": timezone.now() + timedelta(days=5), "location": "Main Hall",
            },
        )
        SchoolEvent.objects.get_or_create(
            school=school, title="Inter-House Sports",
            defaults={
                "event_type": "ACTIVITY", "audience": "ALL",
                "start": timezone.now() + timedelta(days=20), "location": "Sports Field",
            },
        )
        Holiday.objects.get_or_create(
            school=school, name="Founders Day", date=timezone.localdate() + timedelta(days=15)
        )
        for student in students[:5]:
            if student.user:
                Notification.objects.get_or_create(
                    user=student.user, title="New assignment posted",
                    defaults={"message": "Check your assignments for details."},
                )

    def _settings(self, school):
        SchoolSetting.objects.get_or_create(
            school=school,
            defaults={
                "data": {
                    "grading": "Default Scale",
                    "attendance_days": ["MON", "TUE", "WED", "THU", "FRI"],
                }
            },
        )
